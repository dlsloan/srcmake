#include <stdio.h>

//!opt obj-builder-args:= -Wall -Werror
//!opt obj-builder-args+= -fno-exceptions
//!opt link-builder-args:= -fno-exceptions

int main(int argc, const char **argv) {
	printf("Hello World\n");
}