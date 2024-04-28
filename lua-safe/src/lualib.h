/*
** $Id: lualib.h $
** Lua standard libraries
** See Copyright Notice in lua.h
*/


#ifndef lualib_h
#define lualib_h

#include "lua.h"


/* version suffix for environment variable names */
#define LUA_VERSUFFIX          "_" LUA_VERSION_MAJOR "_" LUA_VERSION_MINOR

#include "lcorolib.h"
#include "lbaselib.h"
#include "ltablib.h"
#include "lstrlib.h"
#include "lutf8lib.h"
#include "lmathlib.h"
#include "ldblib.h"
#include "linit.h"

#endif
