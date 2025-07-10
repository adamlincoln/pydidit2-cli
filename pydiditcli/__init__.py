import typer


def _main(name: str):
    print(f"Hello {name}")

def main():
    typer.run(_main)

if __name__ == "__main__":
    main()
