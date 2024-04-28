#ifndef __LSTRLIB_H__
#define __LSTRLIB_H__

#include "lua.h"

#define LUA_STRLIBNAME	"string"
LUAMOD_API int (luaopen_string) (lua_State *L);

#endif//__LSTRLIB_H__