# Re-encode a DataTable JSON (from dt2json.py) back into the cooked unversioned .uexp
# usage: json2dt.py <orig_base> <edited.json> <out_base>   (orig .uasset/.uexp supply name map + header bytes)
import struct,sys,json,os,shutil
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import reflect,dt2json
from dt2json import SIMPLE
class W:
    def __init__(s,names): s.b=bytearray(); s.names=names; s.idx={n:i for i,n in enumerate(names)}
    def p(s,fmt,*v): s.b+=struct.pack('<'+fmt,*v)
    def fname(s,n):
        if n in s.idx: return s.p('iI',s.idx[n],0)
        base,_,num=n.rpartition('_')
        if base in s.idx and num.isdigit() and not(len(num)>1 and num[0]=='0'):
            return s.p('iI',s.idx[base],int(num)+1)
        raise KeyError(f'name not in name map: {n}')
    def fstr(s,v):
        if v=='': return s.p('i',0)
        try: e=v.encode('ascii')+b'\0'; s.p('i',len(e)); s.b+=e
        except UnicodeEncodeError: e=v.encode('utf-16le')+b'\0\0'; s.p('i',-(len(e)//2)); s.b+=e
def enumval(p,v):
    if isinstance(v,int): return v
    for k,n in (p.get('enum') or {}).get('values',{}).items():
        if n==v: return k
    raise KeyError(f'{p["name"]}: unknown enum value {v}')
def is_zero(p,v):
    t=p['type']
    if t in SIMPLE or t=='Byte': return (enumval(p,v) if p.get('enum') else v)==0
    if t=='Bool': return v is False
    if t=='Enum': return enumval(p,v)==0
    if t in('Array','Set','Map'): return len(v)==0
    if t=='Name': return v=='None'
    return False
def put(w,p,v):
    t=p['type']
    if t in SIMPLE: return w.p(SIMPLE[t],v)
    if t=='Byte': return w.p('B',enumval(p,v) if p.get('enum') else v)
    if t=='Bool': return w.p('B',1 if v else 0)
    if t=='Enum':
        f={'Byte':'B','Int':'i','Int8':'b','Int16':'h','UInt16':'H','UInt32':'I','Int64':'q'}.get(p.get('underlying','Byte'),'B')
        return w.p(f,enumval(p,v))
    if t=='Name': return w.fname(v)
    if t=='Str': return w.fstr(v)
    if t in('Array','Set'):
        if t=='Set': w.p('i',0)
        w.p('i',len(v))
        for x in v: put(w,p['inner'],x)
        return
    if t=='Map':
        w.p('i',0); w.p('i',len(v))
        for k,x in v: put(w,p['key'],k); put(w,p['value'],x)
        return
    if t=='Struct' and p['struct'] not in('Vector','Rotator','Vector2D','LinearColor','Color','Guid'):
        return put_struct(w,p['struct'],v)
    raise ValueError(f'encode unsupported: {t} {p.get("struct")}')
def put_struct(w,sn,row):
    sch=reflect.schema(sn); flat=[]
    for p in sch: flat+=[p]*p['dim']
    if any(p['dim']!=1 for p in sch): raise ValueError('static arrays not supported')
    present=[(i,p) for i,p in enumerate(flat) if p['name'] in row]
    # header fragments: (skip, hasZero, count, last)
    frags=[]; prev=-1; zeros=[]
    for i,p in present:
        z=is_zero(p,row[p['name']])
        if frags and i==prev+1 and frags[-1][2]<127: frags[-1][2]+=1
        else: frags.append([i-prev-1,False,1])
        if z: frags[-1][1]=True
        prev=i
    if not frags: frags=[[0,False,0]]
    # zero mask covers every value in fragments flagged hasZero
    k=0
    for f in frags:
        for _ in range(f[2]):
            i,p=present[k]; k+=1
            if f[1]: zeros.append(is_zero(p,row[p['name']]))
    for n,(skip,hz,cnt) in enumerate(frags):
        assert skip<128
        w.p('H',skip|(0x80 if hz else 0)|(0x100 if n==len(frags)-1 else 0)|(cnt<<9))
    if zeros:
        nb=1 if len(zeros)<=8 else 2 if len(zeros)<=16 else ((len(zeros)+31)//32)*4
        w.b+=sum(1<<j for j,z in enumerate(zeros) if z).to_bytes(nb,'little')
    for i,p in present:
        v=row[p['name']]
        if not is_zero(p,v): put(w,p,v)
def encode(orig_base,js):
    ua=open(orig_base+'.uasset','rb').read(); d=open(orig_base+'.uexp','rb').read()
    names=dt2json.load_names(ua)
    rs,sch,rows=dt2json.decode(orig_base)
    # locate where row data begins (same probing as decoder)
    for start in range(96):
        r=dt2json.R(d,names); r.o=start
        try:
            if r.u('i')!=len(rows): continue
            for _ in rows: r.fname(); dt2json.struct_val(r,rs)
            if r.o==len(d)-4: break
        except Exception: pass
    w=W(names); w.b+=d[:start]; w.p('i',len(js['Rows']))
    for k,row in js['Rows'].items(): w.fname(k); put_struct(w,rs,row)
    w.b+=d[-4:]
    return bytes(w.b)
def patch_sizes(ua,old_len,new_len):
    # single-export DataTable: export SerialSize (followed by SerialOffset==len(uasset)) and summary BulkDataStartOffset
    d=new_len-old_len; L=len(ua)
    ser=[i for i in range(len(ua)-16) if struct.unpack_from('<qq',ua,i)==(old_len-4,L)]
    bulk=[i for i in range(len(ua)-8) if struct.unpack_from('<q',ua,i)[0]==L+old_len-4]
    if len(ser)!=1 or len(bulk)!=1: raise SystemExit(f'cannot locate size fields uniquely: serial={ser} bulk={bulk}')
    struct.pack_into('<q',ua,ser[0],old_len-4+d); struct.pack_into('<q',ua,bulk[0],L+old_len-4+d)
    return ua
if __name__=='__main__':
    orig,jf,out=sys.argv[1:4]
    js=json.load(open(jf,encoding='utf-8'))
    new=encode(orig,js); old=open(orig+'.uexp','rb').read()
    ua=bytearray(open(orig+'.uasset','rb').read())
    if len(new)!=len(old):
        ua=patch_sizes(ua,len(old),len(new))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out+'.uasset','wb').write(ua)
    open(out+'.uexp','wb').write(new)
    print(f'{os.path.basename(out)}: {sum(a!=b for a,b in zip(old,new))} bytes changed')
