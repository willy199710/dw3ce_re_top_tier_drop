# Decode a cooked (unversioned) UE5 DataTable .uasset/.uexp into JSON using reflect.py schemas
import struct,sys,json,re,os
sys.path.insert(0,os.path.dirname(__file__))
import reflect
def load_names(ua):
    # summary: ..., PackageName FString, PackageFlags u32, NameCount i32, NameOffset i32
    p=ua.find(b'/Game/')-4; n=struct.unpack_from('<i',ua,p)[0]; p+=4+n+4
    cnt,off=struct.unpack_from('<ii',ua,p)
    names=[]
    for _ in range(cnt):
        n=struct.unpack_from('<i',ua,off)[0]
        if n<0: names.append(ua[off+4:off+4-2*n-2].decode('utf-16le')); off+=4-2*n+4
        else: names.append(ua[off+4:off+4+n-1].decode('latin1')); off+=4+n+4
    return names
class R:
    def __init__(s,d,names): s.d=d; s.o=0; s.names=names
    def u(s,fmt):
        v=struct.unpack_from('<'+fmt,s.d,s.o); s.o+=struct.calcsize('<'+fmt); return v[0]
    def fname(s):
        i=s.u('i'); n=s.u('I'); b=s.names[i] if 0<=i<len(s.names) else f'?{i}'
        return b+(f'_{n-1}' if n else '')
    def fstr(s):
        n=s.u('i')
        if n==0: return ''
        if n<0: v=s.d[s.o:s.o-2*n].decode('utf-16le')[:-1]; s.o+=-2*n
        else: v=s.d[s.o:s.o+n].decode('utf-8','replace')[:-1]; s.o+=n
        return v
    def header(s):
        frags=[]
        while True:
            v=s.u('H'); frags.append((v&0x7f,(v>>7)&1,v>>9))
            if v&0x100: break
        idx=0; props=[]; nz=0
        for skip,hz,num in frags:
            idx+=skip
            for k in range(num): props.append((idx,hz)); idx+=1
            if hz: nz+=num
        zm=0
        if nz:
            nb=1 if nz<=8 else 2 if nz<=16 else ((nz+31)//32)*4
            zm=int.from_bytes(s.d[s.o:s.o+nb],'little'); s.o+=nb
        out=[];zi=0
        for i,hz in props:
            z=False
            if hz: z=bool(zm>>zi&1); zi+=1
            out.append((i,z))
        return out
SIMPLE={'Int8':'b','Int16':'h','Int':'i','Int64':'q','UInt16':'H','UInt32':'I','UInt64':'Q','Float':'f','Double':'d'}
def enumname(p,v):
    e=p.get('enum') or {}
    return e.get('values',{}).get(v,v)
def zero(p):
    t=p['type']
    if t in SIMPLE or t in('Byte',): return 0
    if t=='Bool': return False
    if t=='Enum': return enumname(p,0)
    if t in('Str','Text'): return ''
    if t=='Name': return 'None'
    if t in('Array','Set','Map'): return []
    return None
def val(r,p):
    t=p['type']
    if t in SIMPLE: return r.u(SIMPLE[t])
    if t=='Byte':
        v=r.u('B'); return enumname(p,v) if p.get('enum') else v
    if t=='Bool': return bool(r.u('B'))
    if t=='Enum':
        v=r.u({'Byte':'B','Int':'i','Int8':'b','Int16':'h','UInt16':'H','UInt32':'I','Int64':'q'}.get(p.get('underlying','Byte'),'B'))
        return enumname(p,v)
    if t=='Name': return r.fname()
    if t=='Str': return r.fstr()
    if t=='Text':
        flags=r.u('I'); ht=r.u('b')
        if ht==-1:
            has=r.u('I'); return r.fstr() if has else ''
        if ht==0: return {'ns':r.fstr(),'key':r.fstr(),'src':r.fstr()}
        if ht==11: return {'table':r.fname(),'key':r.fstr()}
        raise ValueError(f'text history {ht}')
    if t=='SoftObject': return {'path':r.fname(),'asset':r.fname(),'sub':r.fstr()}
    if t in('Object','Class'): return r.u('i')
    if t in('Array','Set'):
        if t=='Set': r.u('i')
        n=r.u('i'); return [val(r,p['inner']) for _ in range(n)]
    if t=='Map':
        r.u('i'); n=r.u('i'); return [[val(r,p['key']),val(r,p['value'])] for _ in range(n)]
    if t=='Struct':
        sn=p['struct']
        if sn in('Vector','Rotator'): return [r.u('d') for _ in range(3)]
        if sn=='Vector2D': return [r.u('d') for _ in range(2)]
        if sn in('LinearColor',): return [r.u('f') for _ in range(4)]
        if sn=='Color': return list(r.d[r.o:r.o+4]) if not setattr(r,'o',r.o+4) else None
        if sn=='Guid': return r.d[r.o:(setattr(r,'o',r.o+16) or r.o)].hex()
        return struct_val(r,sn)
    raise ValueError(f'unsupported {t} {p}')
def struct_val(r,sn):
    sch=reflect.schema(sn); flat=[]
    for p in sch: flat+= [p]*p['dim']
    out={}
    for i,z in r.header():
        p=flat[i]; out[p['name']]= zero(p) if z else val(r,p)
    return out
def decode(base):
    ua=open(base+'.uasset','rb').read(); d=open(base+'.uexp','rb').read()
    names=load_names(ua)
    rowstruct=[n for n in names if n.endswith('_TableRow') or n.endswith('Row')][-1]
    sch=reflect.schema(rowstruct)
    for start in range(0,96):
        r=R(d,names); r.o=start
        try:
            n=r.u('i')
            if not 0<n<100000: continue
            rows={}
            for _ in range(n):
                k=r.fname(); rows[k]=struct_val(r,rowstruct)
            if r.o==len(d)-4: return rowstruct,sch,rows
        except Exception as e: pass
    raise SystemExit('could not decode '+base)
if __name__=='__main__':
    for b in sys.argv[1:]:
        rs,sch,rows=decode(b)
        json.dump({'RowStruct':rs,'Rows':rows},open(b+'.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
        print(os.path.basename(b),rs,len(rows),'rows ->',b+'.json')
