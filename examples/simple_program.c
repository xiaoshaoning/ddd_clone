/*
Simple C program for testing DDD Clone
Compile with: gcc -g -o simple_program simple_program.c
*/

#include <stdio.h>

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int main() {
    int number = 5;
    int fact_result, fib_result;

    printf("Calculating factorial and fibonacci for %d\n", number);

    // Calculate factorial
    fact_result = factorial(number);
    printf("Factorial of %d is %d\n", number, fact_result);

    // Calculate fibonacci
    fib_result = fibonacci(number);
    printf("Fibonacci number at position %d is %d\n", number, fib_result);

    // Array example
    int arr[5] = {1, 2, 3, 4, 5};
    int sum = 0;

    for (int i = 0; i < 5; i++) {
        sum += arr[i];
    }

    printf("Sum of array elements: %d\n", sum);

    return 0;
}