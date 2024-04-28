#ifndef __LMATHLIB_H__
#define __LMATHLIB_H__

#include "lua.h"

#define LUA_MATHLIBNAME	"math"
LUAMOD_API int (luaopen_math) (lua_State *L);

#endif//__LMATHLIB_H__