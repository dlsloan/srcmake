#ifndef __LINIT_H__
#define __LINIT_H__

#include "lua.h"

/* open all previous libraries */
LUALIB_API void (luaL_openlibs) (lua_State *L);

#endif//__LINIT_H__