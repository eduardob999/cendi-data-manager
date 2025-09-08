import pandas as pd
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from colorama import init, Fore, Style
import datetime
import os


def validate_file(file_path):
    """Validate if the file exists, is readable, and is a CSV file."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return False
    if not os.access(file_path, os.R_OK):
        print(f"File {file_path} is not readable.")
        return False
    if not file_path.endswith('.csv'):
        print(f"File {file_path} is not a CSV file.")
        return False
    return True


def initialize_screen():
    """Initialize the main screen with program information."""
    init(autoreset=True)
    print(Fore.GREEN + "Attendance data updater")
    print(Fore.GREEN + "Version 0.2")
    print(Fore.GREEN + "by Eduardo Bogado (2025)")
    print("")
    print("Press Ctrl+C to interrupt and exit the program.")
    print("")


def get_date_input():
    """Prompt the user to enter a valid date."""
    while True:
        date_input = input(
            "Enter the date for attendance (e.g., 2023-10-01): ")
        try:
            date = datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
            return date
        except ValueError:
            print("Invalid date format. Please enter the date in YYYY-MM-DD format.")


def main():
    # Validate the main file
    main_file_path = 'nomina.csv'
    if not validate_file(main_file_path):
        exit(1)

    # Initialize the main screen
    initialize_screen()

    # Load the main CSV file
    main_df = pd.read_csv(main_file_path)

    try:
        # Get the date input
        date = get_date_input()

        print("Instructions:")
        print(" - Enter CÉDULA to mark attendance")
        print(" - Type 'done' to finish")
        print(" - Type 'undo' to revert the last entry")
        print(" - Type 'add' to add new personnel")
        print("")

        # Create a new column for attendance if it doesn't exist
        attendance_column = str(date)
        if attendance_column not in main_df.columns:
            main_df[attendance_column] = 0  # Initialize with 0

        # Create a completer for CÉDULA values
        cedula_completer = WordCompleter(
            [str(cedula) for cedula in main_df['CÉDULA']], ignore_case=True)

        # Track the entries for undo functionality
        entry_history = []

        try:
            # Enter attendance data for each personnel
            while True:
                cedula = prompt("Enter CÉDULA: ", completer=cedula_completer)
                if cedula.lower() == 'done':
                    break
                elif cedula.lower() == 'undo':
                    if entry_history:
                        last_entry = entry_history.pop()
                        main_df.loc[main_df['CÉDULA'] ==
                                    last_entry, attendance_column] -= 1
                        print(f"Last entry for CÉDULA {last_entry} undone.")
                    else:
                        print("No entry to undo.")
                elif cedula.lower() == 'add':
                    new_cedula = input("Enter new CÉDULA: ")
                    new_apellidos = input("Enter new APELLIDOS: ")
                    new_nombres = input("Enter new NOMBRES: ")
                    if new_cedula.isdigit():
                        new_row = pd.DataFrame({
                            'CÉDULA': [int(new_cedula)],
                            'APELLIDOS': [new_apellidos],
                            'NOMBRES': [new_nombres],
                            attendance_column: [0]
                        })
                        main_df = pd.concat(
                            [main_df, new_row], ignore_index=True)
                        # Update the completer with the new CÉDULA
                        cedula_completer = WordCompleter(
                            [str(cedula) for cedula in main_df['CÉDULA']], ignore_case=True)
                        print(
                            f"New personnel {new_nombres} {new_apellidos} added.")
                    else:
                        print("Invalid CÉDULA. Please enter a numeric value.")
                elif cedula.isdigit():
                    cedula = int(cedula)
                    if cedula in main_df['CÉDULA'].values:
                        main_df.loc[main_df['CÉDULA'] ==
                                    cedula, attendance_column] += 1
                        entry_history.append(cedula)
                    else:
                        print(f"CÉDULA {cedula} not found in the main CSV.")
                else:
                    print("Invalid CÉDULA. Please enter a numeric value.")
        except KeyboardInterrupt:
            print("\nOperation interrupted. Changes were not saved.")

        # Save the updated DataFrame back to the CSV file
        main_df.to_csv(main_file_path, index=False)
        print("Attendance data saved successfully.")

    except KeyboardInterrupt:
        print("\nOperation interrupted. Exiting without changes.")


if __name__ == "__main__":
    main()
