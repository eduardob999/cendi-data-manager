# Deploy instructions

1. **Install PyInstaller**:
   ```sh
   pip install pyinstaller
   ```

3. **Create a requirements.txt** 
  
  file with the following content:

   ```plaintext
   pandas
   prompt_toolkit
   ```

4. **Package the script using PyInstaller**:
   ```sh
   pyinstaller --onefile add_date.py
   ```

   This command will create a standalone executable in the `dist` directory.

5. **Provide the executable to the user**:
   - Copy the nomina.csv

 file and the executable (`add_date` or `add_date.exe` on Windows) from the `dist` directory to a folder.
   - Instruct the user to run the executable by double-clicking it (on Windows) or running it from the terminal (on Linux/Mac).

# **Instructions for the user**:
   - Place the nomina.csv file in the same directory as the executable.
   - Run the executable by double-clicking it (on Windows) or using the terminal (on Linux/Mac).
   - Follow the prompts to enter the date and `CÉDULA` values.