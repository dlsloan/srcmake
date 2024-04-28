#ifndef __LTABLIB_H__
#define __LTABLIB_H__

#include "lua.h"

#define LUA_TABLIBNAME	"table"
LUAMOD_API int (luaopen_table) (lua_State *L);

#endif//__LTAGLIB_H__