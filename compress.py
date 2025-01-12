import os
import subprocess
import argparse

def compress_folders(source_directory):
    # Change to the source directory
    os.chdir(source_directory)

    # Loop over each item in the directory
    for folder in os.listdir(source_directory):
        folder_path = os.path.join(source_directory, folder)

        # Check if it's a directory
        if os.path.isdir(folder_path):
            # Define the output archive name
            archive_name = f"{folder}.7z"
            
            # Command to compress the folder using 7zip with the given flags
            command = [
                "7z", "a", "-mx=9", "-mfb=64", "-md=32m", "-ms=on",
                archive_name, folder_path
            ]
            
            try:
                # Run the command
                subprocess.run(command, check=True)
                print(f"Compressed {folder} into {archive_name}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to compress {folder}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Compress folders in a directory into separate 7z archives.")
    parser.add_argument("source_directory", help="Path to the directory containing folders to compress")
    args = parser.parse_args()

    if not os.path.isdir(args.source_directory):
        print(f"Error: '{args.source_directory}' is not a valid directory.")
        return

    compress_folders(args.source_directory)

if __name__ == "__main__":
    main()
