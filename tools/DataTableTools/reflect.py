# Static UE5 reflection reader: row-struct schemas from Z_Construct FStructParams in the shipping exe
import re,struct,functools,os
# game install dir can be overridden with the DW3CE_GAME_DIR environment variable
GAME_DIR=os.environ.get("DW3CE_GAME_DIR",r"G:\SteamLibrary\steamapps\common\DW3CE_RE")
EXE=os.path.join(GAME_DIR,"DW3CE_RE","Binaries","Win64","DW3CE_RE-Win64-Shipping.exe")
m=open(EXE,'rb').read()
pe=struct.unpack_from('<I',m,0x3c)[0]; ns=struct.unpack_from('<H',m,pe+6)[0]; opt=struct.unpack_from('<H',m,pe+20)[0]
BASE=struct.unpack_from('<Q',m,pe+24+24)[0]
SECS=[]
for i in range(ns):
    o=pe+24+opt+i*40; vs,va,rs,ra=struct.unpack_from('<4I',m,o+8); SECS.append((va,vs,ra,rs))
def off2va(o):
    for va,vs,ra,rs in SECS:
        if ra<=o<ra+rs: return BASE+va+(o-ra)
def va2off(v):
    for va,vs,ra,rs in SECS:
        if BASE+va<=v<BASE+va+rs: return ra+(v-BASE-va)
def q(o): return struct.unpack_from('<Q',m,o)[0]
def cstr(v):
    o=va2off(v)
    if o is None: return None
    e=m.find(b'\0',o); return m[o:e].decode('latin1')
GEN={0:'Byte',1:'Int8',2:'Int16',3:'Int',4:'Int64',5:'UInt16',6:'UInt32',7:'UInt64',0xA:'Float',0xB:'Double',0xC:'Bool',
     0xD:'SoftClass',0xE:'WeakObject',0xF:'LazyObject',0x10:'SoftObject',0x11:'Class',0x12:'Object',0x13:'Interface',
     0x14:'Name',0x15:'Str',0x16:'Array',0x17:'Map',0x18:'Set',0x19:'Struct',0x1D:'Text',0x1E:'Enum',0x1F:'FieldPath',0x20:'LWCReal'}
# code-gen funcs like Z_Construct_UScriptStruct_X / Z_Construct_UEnum_X: find the params struct a func loads via 'lea rcx,[rip+x]'
def func_target_params(fva):
    o=va2off(fva)
    if o is None: return None
    code=m[o:o+96]
    for i in range(len(code)-7):
        if code[i:i+3] in (b'\x48\x8d\x15',b'\x48\x8d\x0d'):
            disp=struct.unpack_from('<i',code,i+3)[0]; tgt=fva+i+7+disp
            return tgt
    return None
@functools.lru_cache(None)
def enum_info(fva):
    p=func_target_params(fva)
    if p is None: return None
    for cand in (p,):
        po=va2off(cand)
        # FEnumParams: Outer, DisplayNameFunc, NameUTF8, CppTypeUTF8, EnumeratorParams, ..., NumEnumerators
        name=cstr(q(po+16)); arr=q(po+32)
        n=struct.unpack_from('<h',m,po+44)[0]
        ao=va2off(arr)
        if ao is None or not (0<n<5000): return {'name':name}
        vals={}
        for k in range(n):
            s=cstr(q(ao+k*16)); v=struct.unpack_from('<q',m,ao+k*16+8)[0]; vals[v]=s.split('::')[-1]
        return {'name':name,'values':vals}
@functools.lru_cache(None)
def struct_name_from_func(fva):
    p=func_target_params(fva)
    if p is None: return None
    s=cstr(q(va2off(p)+24))
    return s
def parse_prop(po):
    name=cstr(q(po)); gen=m[po+24]; t=GEN.get(gen&0x3f,hex(gen))
    dim,off=struct.unpack_from('<HH',m,po+48)
    p={'name':name,'type':t,'offset':off,'dim':dim}
    if t in('Byte',) and q(po+56): p['enum']=enum_info(q(po+56))
    if t=='Enum': p['enum']=enum_info(q(po+56))
    if t=='Struct': p['struct']=struct_name_from_func(q(po+56))
    if t=='Bool': p['boolsize']=m[po+52]
    return p
@functools.lru_cache(None)
def find_struct(name):
    nb=b'\0'+name.encode()+b'\0'
    for x in re.finditer(re.escape(nb),m):
        va=off2va(x.start()+1)
        for r in re.finditer(re.escape(struct.pack('<Q',va)),m):
            so=r.start()-24
            arr,nprop,size=q(so+32),*struct.unpack_from('<HH',m,so+40)
            ao=va2off(arr)
            if ao is None and nprop!=0: continue
            props=[parse_prop(va2off(q(ao+i*8))) for i in range(nprop)]
            # drop inner props (enum underlying / array inner): they share the parent's offset and follow it
            out=[]
            out=[]; i=0
            while i<len(props):
                p=props[i]; nxt=props[i+1] if i+1<len(props) else None
                if p['name']=='UnderlyingType' and nxt and nxt['type']=='Enum':
                    nxt['underlying']=p['type']; i+=1; continue
                if nxt and nxt['type'] in('Array','Set') and nxt['name']==p['name'] and 'inner' not in nxt:
                    nxt['inner']=p; i+=1; continue
                if nxt and i+2<len(props) and props[i+2]['type']=='Map' and props[i+2]['name']==p['name'] and nxt['name']==p['name']+'_Key':
                    props[i+2]['value']=p; props[i+2]['key']=nxt; i+=2; continue
                out.append(p); i+=1
            sup=q(so+8); supname=struct_name_from_func(sup) if sup else None
            return {'name':name,'size':size,'super':supname,'props':out}
    return None
def schema(name):
    s=find_struct(name)
    if s is None: return []
    base=schema(s['super']) if s['super'] and s['super']!='TableRowBase' else []
    return base+s['props']
if __name__=='__main__':
    import sys,json
    for n in sys.argv[1:]:
        s=find_struct(n); print(n,'size',s and s['size'],'super',s and s['super'])
        for p in schema(n): print('  ',{k:(v if k!='enum' else (v and v.get('name'))) for k,v in p.items()})
@functools.lru_cache(None)
def imports():
    dd=pe+24+112  # PE32+ data directories
    irva,irsz=struct.unpack_from('<II',m,dd+8)
    res={}; o=va2off(BASE+irva)
    while True:
        oft,ts,fc,namerva,ft=struct.unpack_from('<5I',m,o)
        if namerva==0: break
        dll=cstr(BASE+namerva); t=va2off(BASE+(oft or ft)); k=0
        while True:
            e=q(t+k*8)
            if e==0: break
            nm=f'#{e&0xffff}' if e>>63 else cstr(BASE+(e&0x7fffffff)+2)
            res[BASE+ft+k*8]=f'{dll}!{nm}'; k+=1
        o+=20
    return res
