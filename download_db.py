#to autodownload, this script can be put on the 'before connection' section of database configuration
import requests
import sqlite3
import os

# Set the current working directory to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

url = 'https://www.pythonanywhere.com/user/evaluerlisibilite/files/home/evaluerlisibilite/sentences.db'

# Get these from Storage Inspector in the browser
cookies = {
    'csrftoken': 'rATNXmO27RzAfsrxuiPU8KvwyH787xQAxXkkfnrz3VIXxsGUduRHLj7Ev9phP9Sb',
    'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
    'sessionid': 'fpft9kc1lt4h6avx4aoq19xw4hloddze',
}

response = requests.get(url, cookies=cookies)

# Check if the request was successful
if response.status_code == 200:
    content_type = response.headers.get('Content-Type')
    if 'text/html' not in content_type:
        # Save the content to a temporary file
        temp_file_path = 'data/poll_results_tmp.db'
        with open(temp_file_path, 'wb') as file:
            file.write(response.content)
        print("Temporary file downloaded successfully.")

        # Verify the temporary file is a valid SQLite database
        try:
            conn = sqlite3.connect(temp_file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ratings")
            count = cursor.fetchone()[0]
            print(f"The database contains {count} records in the 'ratings' table.")
            conn.close()

            # Replace the old file with the new one if it's valid
            os.replace(temp_file_path, 'data/poll_results.db')
            print("Temporary file verified and replaced the old file successfully.")
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            print("The downloaded file is not a valid SQLite database or the 'ratings' table does not exist.")
            print(f"Error: {e}")
            os.remove(temp_file_path)
            print("Invalid temporary file removed.")
    else:
        print("Received an HTML response instead of a file.")
else:
    print(f"Failed to download file. Status code: {response.status_code}")
