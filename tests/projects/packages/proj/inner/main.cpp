#include <stdio.h>

//!package "../hello_printer.sh"
#include "hello_printer/hello.h"

int main(int argc, const char *argv) {
	printf("%s\n", hello());
}