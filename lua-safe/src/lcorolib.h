#ifndef __LCOROLIB_H__
#define __LCOROLIB_H__

#include "lua.h"

#define LUA_COLIBNAME	"coroutine"
LUAMOD_API int (luaopen_coroutine) (lua_State *L);

#endif//__LCOROLIB_H__