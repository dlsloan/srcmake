import rre, nfa

env = rre.env.parse(b'''
hex:(0x){![a-fA-F0-9]+:Expected hex digit [a-fA-F0-9]}
bin:(0b){![01]+:Expected binary digit [01]}
octal:(0o){![0-7]+:"Expected octal digit [0-7]}
integer:[0-9]+
float:[0-9]+(\.[0-9]+)?([eE][+-]?{![0-9]+:Expected decimal digit [0-9]})?
number:{:hex}|{:bin}|{:octal}|{:integer}|{:float}

double_string:"{!([^"\\\\]|\\.)*":Expected unescaped closing double quotes}
single_string:'{!([^'\\\\]|\\.)*':Expected unescaped closing single quotes}
string:{:double_string}|{:single_string}

literal:{:string}|{:number}

inline_comment://[^\\n]*(\\n|\\0)
multiline_comment:/\*{!([^*]|\*[^/])*\*/:Expected comment close: */}
comment:{:inline_comment}|{:multiline_comment}

ws:({:comment}|[ \\t\\n])+

name:[a-zA-Z_][a-zA-Z0-9_]*
full_name:{:name}(\.{:name})*

import:import{:ws}{:full_name};

root_element:{:import}
root:({:ws}?{:root_element})*{:ws}?
''')

parser = rre.parse(b'[a-zA-Z_][a-zA-Z0-9_]*').to_nfa()
match = parser.parse(b'''name''', env=env)
print(repr(match))