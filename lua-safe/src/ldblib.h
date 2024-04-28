#ifndef __LDBLIB_H__
#define __LDBLIB_H__

#include "lua.h"

#define LUA_DBLIBNAME	"debug"
LUAMOD_API int (luaopen_debug) (lua_State *L);

#endif//__LDBLIB_H__