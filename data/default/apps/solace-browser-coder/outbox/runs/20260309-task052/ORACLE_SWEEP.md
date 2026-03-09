# ORACLE_SWEEP

Command:
```bash
for run in 1 2 3; do
  pytest -q tests/test_cloud_twin_docker.py
done
```

Result:
```text
run 1
.......                                                                  [100%]
7 passed in 0.09s
run 2
.......                                                                  [100%]
7 passed in 0.09s
run 3
.......                                                                  [100%]
7 passed in 0.09s
```

Regression pass:
```bash
pytest -q tests/test_cloud_twin.py tests/test_yinyang_instructions.py tests/test_deployment.py
```

```text
415 passed in 2.00s
```
