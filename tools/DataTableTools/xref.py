import reflect as R,numpy as np,sys
m=R.m
tva,tvs,tra,trs=[s for s in R.SECS if s[0]==0x1000][0]
_b=np.frombuffer(m,dtype=np.uint8,count=trs,offset=tra)
_rel=(_b[0:-3].astype(np.int64)|(_b[1:-2].astype(np.int64)<<8)|(_b[2:-1].astype(np.int64)<<16)|(_b[3:].astype(np.int64)<<24))
_rel=np.where(_rel>=2**31,_rel-2**32,_rel)
_nxt=R.BASE+tva+np.arange(len(_rel),dtype=np.int64)+4+_rel
del _rel
def xrefs(g,slack=(0,1,4)):
    mask=np.zeros(len(_nxt),bool)
    for s in slack: mask|=(_nxt==g-s)
    return [R.BASE+tva+int(h) for h in np.nonzero(mask)[0]]
def calls(g):
    hits=np.nonzero((_nxt==g)&((_b[:-3]==0)|True))[0]
    return [R.BASE+tva+int(h)-1 for h in hits if m[tra+int(h)-1] in (0xE8,0xE9)]
from capstone import *
md=Cs(CS_ARCH_X86,CS_MODE_64)
def dis(va,n=200,stop_ret=True):
    o=R.va2off(va); out=[]
    for ins in md.disasm(m[o:o+n*8],va):
        out.append(ins)
        if len(out)>=n or (stop_ret and ins.mnemonic=='ret' ): break
    return out
def func_start(va):
    # use .pdata runtime functions
    po=[s for s in R.SECS if s[0]==0xa9fc000][0]
    rva=va-R.BASE
    arr=np.frombuffer(m,dtype=np.uint32,count=(po[3]//12)*3,offset=po[2]).reshape(-1,3); arr=arr[arr[:,0]!=0]
    i=np.searchsorted(arr[:,0],rva,side='right')-1
    while i>0 and not(arr[i,0]<=rva<arr[i,1]): i-=1
    return R.BASE+int(arr[i,0]),R.BASE+int(arr[i,1])
