import struct,sys
d=open(sys.argv[1],'rb').read()
H=struct.unpack_from
hs,ec,cbc,cbs,cmc,cml,cbsz,dis,pc=H('<9I',d,20)
seeds=H('<I',d,84)[0]; nophc=H('<I',d,96)[0]; flags=d[80]
o=hs+ec*12+ec*10+seeds*4+nophc*4+cbc*12+cmc*cml
if flags&4: 
    hsz=H('<i',d,o)[0]; o+=4+hsz*2+cbc*20
p=o
def fstr():
    global p
    n=H('<i',d,p)[0]; p+=4
    if n<0: s=d[p:p-2*n].decode('utf-16le')[:-1]; p+=-2*n
    else: s=d[p:p+n].decode('latin1')[:-1]; p+=n
    return s
mount=fstr()
n=H('<I',d,p)[0];p+=4; dirs=[H('<4I',d,p+i*16) for i in range(n)]; p+=n*16
n=H('<I',d,p)[0];p+=4; files=[H('<3I',d,p+i*12) for i in range(n)]; p+=n*12
n=H('<I',d,p)[0];p+=4; st=[fstr() for _ in range(n)]
N=0xFFFFFFFF
def walk(di,path):
    name,child,sib,ff=dirs[di]
    path=path+(st[name]+'/' if name!=N else '')
    f=ff
    while f!=N:
        print(mount+path+st[files[f][0]]); f=files[f][1]
    c=child
    while c!=N:
        walk(c,path); c=dirs[c][2]
walk(0,'')
