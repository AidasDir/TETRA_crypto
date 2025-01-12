#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <pthread.h>

#define NUM_THREADS 16
#define COMMAND_BUFFER_SIZE 256
#define LINE_BUFFER_SIZE 128
#define OUTPUT_SIZE 11

// Function to generate the next hexadecimal value as a string
char *hex_inc(int num) {
    char *hex_value = malloc(11); // Allocate memory for 10 characters + null terminator
    if (hex_value == NULL) {
        perror("malloc failed");
        exit(EXIT_FAILURE);
    }
    sprintf(hex_value, "%08x", num + 1); // Increment and format
    return hex_value;
}

// Struct to pass arguments to threads
typedef struct {
    int start;
    int end;
    char *target;
    int *found;
    pthread_mutex_t *mutex;
} thread_args;

// Thread function
void *thread_func(void *arg) {
    thread_args *args = (thread_args *)arg;
    char command[COMMAND_BUFFER_SIZE];
    char line[LINE_BUFFER_SIZE];
    char output[OUTPUT_SIZE];
    char *to_increment;
    FILE *fp;

    for (int i = args->start; i <= args->end; i++) {
        // Generate the next hex value
        to_increment = hex_inc(i);

        // Construct the command string
        snprintf(command, sizeof(command),
                 "/home/nirvana/TETRA_crypto/gen_ks 1 110 30 06 1 0 %s", to_increment);

        // Execute the command
        fp = popen(command, "r");
        if (fp == NULL) {
            perror("popen failed");
            free(to_increment);
            continue;
        }

        // Read the output
        if (fgets(line, sizeof(line), fp) == NULL) {
            pclose(fp);
            free(to_increment);
            continue;
        }

        // Read the second line (expected key)
        if (fgets(line, sizeof(line), fp) != NULL) {
            strncpy(output, line, OUTPUT_SIZE - 1);
            output[OUTPUT_SIZE - 1] = '\0'; // Ensure null termination
        }
        pclose(fp);

        // Check if the output matches the target
        pthread_mutex_lock(args->mutex);
        if (*(args->found)) {
            pthread_mutex_unlock(args->mutex);
            free(to_increment);
            return NULL;
        }
        if (strcmp(output, args->target) == 0) {
            *(args->found) = 1;
            printf("Found key: %s\n", to_increment);
            pthread_mutex_unlock(args->mutex);
            free(to_increment);
            exit(EXIT_SUCCESS);
        }
        pthread_mutex_unlock(args->mutex);

        // Free allocated memory
        free(to_increment);
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <target>\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    char result[11]; // Un tampon pour stocker les 10 premiers caractères + '\0'

    // Copier les 10 premiers caractères dans `result`
    strncpy(result, argv[1], 10);
    result[10] = '\0'; // S'assurer que la chaîne est terminée par '\0'

    char *target = result; // Target value to match
    long total_values = 4294967296; // Total number of values
    int values_per_thread = total_values / NUM_THREADS;
    pthread_t threads[NUM_THREADS];
    thread_args args[NUM_THREADS];
    int found = 0;
    pthread_mutex_t mutex;

    pthread_mutex_init(&mutex, NULL);

    // Create threads
    for (int i = 0; i < NUM_THREADS; i++) {
        args[i].start = i * values_per_thread;
        args[i].end = (i + 1) * values_per_thread - 1;
        args[i].target = target;
        args[i].found = &found;
        args[i].mutex = &mutex;

        if (pthread_create(&threads[i], NULL, thread_func, &args[i]) != 0) {
            perror("pthread_create failed");
            pthread_mutex_destroy(&mutex);
            exit(EXIT_FAILURE);
        }
    }

    // Wait for all threads to finish
    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    pthread_mutex_destroy(&mutex);

    if (!found) {
        printf("Key not found.\n");
    }

    return 0;
}
