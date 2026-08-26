import cv2
import easyocr
import pandas as pd
from datetime import datetime
import os

# Project-relative path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(logs_dir, exist_ok=True)

excel_file = os.path.join(logs_dir, "records.xlsx")

def scanner_thread():
    reader = easyocr.Reader(['en'])
    cap = cv2.VideoCapture(0)
    print("[INFO] Camera started. Press 'q' to quit scanner.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = reader.readtext(frame)
        for (bbox, text, prob) in results:
            if prob > 0.5:
                clean_text = ''.join(filter(str.isalnum, text.strip()))
                if 6 <= len(clean_text) <= 12:  # rough valid plate length
                    now = datetime.now()

                    # Load or create DataFrame
                    try:
                        df = pd.read_excel(excel_file)
                    except FileNotFoundError:
                        df = pd.DataFrame(columns=["Car Number", "First Seen", "Last Seen"])

                    # Ensure columns exist
                    for col in ["Car Number", "First Seen", "Last Seen"]:
                        if col not in df.columns:
                            df[col] = pd.Series(dtype="object")

                    if clean_text in df['Car Number'].astype(str).values:
                        df.loc[df['Car Number'] == clean_text, 'Last Seen'] = now.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[UPDATE] {clean_text} seen again at {now}")
                    else:
                        df.loc[len(df)] = [
                            clean_text,
                            now.strftime("%Y-%m-%d %H:%M:%S"),
                            now.strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        print(f"[NEW] {clean_text} logged at {now}")

                    # Save back to Excel safely
                    try:
                        df.to_excel(excel_file, index=False)
                    except PermissionError:
                        print("[ERROR] Could not write to Excel file. Make sure it's closed in Excel.")

                    # Draw box + plate text on screen
                    (top_left, top_right, bottom_right, bottom_left) = bbox
                    top_left = tuple(map(int, top_left))
                    bottom_right = tuple(map(int, bottom_right))
                    cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
                    cv2.putText(frame, clean_text, (top_left[0], max(0, top_left[1]-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        cv2.imshow("License Plate Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Scanner stopped.")

if __name__ == "__main__":
    scanner_thread()
