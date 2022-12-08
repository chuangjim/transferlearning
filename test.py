import time
import sys
for i in range(10):
    time.sleep(1)
    print(f'hello {i}')
    # sys.stdout.write(f'hello {i}\n')
    # sys.stdout.flush()

print('end')