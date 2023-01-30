#include <stdio.h>

//!package "wrapper.sh"
#include "wrapper/wrapper.h"

int main(int argc, const char *argv) {
	printf("%s\n", hello());
}