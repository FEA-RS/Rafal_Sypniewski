import os

# Wklej tutaj ścieżkę do swojego folderu
folder_path = r"D:\%PRACA_MAGISTERSKA\data\raw\odczyty_czujnikow"

def usun_kopie(path):
    count = 0
    for filename in os.listdir(path):
        # Sprawdzamy czy plik kończy się na " copy.xlsx"
        if filename.endswith(" copy.xlsx"):
            file_path = os.path.join(path, filename)
            os.remove(file_path)
            print(f"Usunięto: {filename}")
            count += 1
    
    print(f"--- Gotowe! Usunięto łącznie {count} plików. ---")

if __name__ == "__main__":
    usun_kopie(folder_path)