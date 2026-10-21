from pathlib import Path

data_path = Path(
    "data/raw/2024/Nat2024us/Nat2024PublicUS.c20250512.r20250708.txt"
)

if not data_path.exists():
    raise FileNotFoundError(
        f"Could not find the data file: {data_path}"
    )

record_count = 0
record_lengths = set()

with data_path.open("r", encoding="latin-1", newline="") as file:
    for line_number, line in enumerate(file, start=1):
        record = line.rstrip("\r\n")
        record_count += 1
        record_lengths.add(len(record))

        if line_number % 500_000 == 0:
            print(f"Checked {line_number:,} records")

print(f"File: {data_path.name}")
print(f"Records: {record_count:,}")
print(f"Record lengths found: {sorted(record_lengths)}")