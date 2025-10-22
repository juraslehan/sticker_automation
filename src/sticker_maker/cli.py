import argparse, os
from .generate import generate_dummy_flow

def main():
    ap = argparse.ArgumentParser(description="Zebra-style label generator (flow mode)")
    ap.add_argument("--out", default="build", help="output folder")
    ap.add_argument("--config", default=os.path.join("templates", "label_config.yaml"))
    ap.add_argument("--ping", action="store_true", help="test the CLI")
    args = ap.parse_args()

    if args.ping:
        print("ok")
        return

    docx_path, pdf_path = generate_dummy_flow(args.out, args.config)
    print(docx_path)
    print(pdf_path)

if __name__ == "__main__":
    main()
