import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ping", action="store_true", help="test the CLI")
    args = ap.parse_args()
    if args.ping:
        print("ok")

if __name__ == "__main__":
    main()
