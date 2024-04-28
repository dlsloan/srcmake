#ifndef __LUTF8LIB_H__
#define __LUTF8LIB_H__

#include "lua.h"

#define LUA_UTF8LIBNAME	"utf8"
LUAMOD_API int (luaopen_utf8) (lua_State *L);

#endif//__LUTF8LIB_H__