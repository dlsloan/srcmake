#include <stdio.h>

//!package "hello_printer"
#include "hello_printer/hello.h"

int main(int argc, const char *argv) {
	printf("%s\n", hello());
}