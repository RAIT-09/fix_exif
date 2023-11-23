import piexif
import argparse
from PIL import Image
from datetime import datetime
import os
import glob
import sys
import signal

class Exif():
    def __init__(self, exif_dict: dict):
        self.exif_dict: dict = exif_dict
        self.Exif_DateTimeOriginal, self.Exif_DateTimeDigitized, self.Exif_OffsetTime, self.zeroth_DateTime = self.get_datetime()

    def get_datetime(self):
        Exif_DateTimeOriginal = None
        Exif_DateTimeDigitized = None
        Exif_OffsetTime = None
        zeroth_DateTime = None

        if not "Exif" in self.exif_dict.keys():
            self.exif_dict["Exif"] = {}

        if piexif.ExifIFD.DateTimeOriginal in self.exif_dict["Exif"].keys():
            try: Exif_DateTimeOriginal = datetime.strptime(self.exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode(), "%Y:%m:%d %H:%M:%S")
            except ValueError: pass
        if piexif.ExifIFD.DateTimeDigitized in self.exif_dict["Exif"].keys():
            try: Exif_DateTimeDigitized = datetime.strptime(self.exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized].decode(), "%Y:%m:%d %H:%M:%S")
            except ValueError: pass
        if piexif.ExifIFD.OffsetTime in self.exif_dict["Exif"].keys():
            Exif_OffsetTime = self.exif_dict["Exif"][piexif.ExifIFD.OffsetTime].decode()

        if "0th" in self.exif_dict.keys():
            if piexif.ImageIFD.DateTime in self.exif_dict["0th"]:
                try: zeroth_DateTime = datetime.strptime(self.exif_dict["0th"][piexif.ImageIFD.DateTime].decode(), "%Y:%m:%d %H:%M:%S")
                except ValueError: pass

        return Exif_DateTimeOriginal, Exif_DateTimeDigitized, Exif_OffsetTime, zeroth_DateTime

    def change_datetime(self, dt: datetime, offset = "+09:00"):
        self.Exif_DateTimeOriginal = dt
        self.exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt.strftime("%Y:%m:%d %H:%M:%S").encode()
        if not self.Exif_DateTimeDigitized is None:
            self.Exif_DateTimeDigitized = dt
            self.exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt.strftime("%Y:%m:%d %H:%M:%S").encode()
        self.Exif_OffsetTime = offset
        self.exif_dict["Exif"][piexif.ExifIFD.OffsetTime] = offset.encode()
        if not self.zeroth_DateTime is None:
            self.zeroth_DateTime = dt
            self.exif_dict["0th"][piexif.ImageIFD.DateTime] = dt.strftime("%Y:%m:%d %H:%M:%S").encode()

def get_modified_time(file_path: str) -> datetime:
    time: float = os.path.getmtime(file_path)
    modified_time: datetime = datetime.fromtimestamp(time)
    return modified_time

def get_exif(img: Image):
    if "exif" in img.info.keys():
        exif_dict: dict = piexif.load(img.info["exif"])
    else:
        exif_dict: dict = {}
    return Exif(exif_dict)

def save(img: Image, file_path: str, sr: os.stat_result, exif: Exif):
    exif_bytes = piexif.dump(exif.exif_dict)
    img.save(file_path, exif=exif_bytes)
    os.utime(path=file_path, times=(sr.st_atime, exif.Exif_DateTimeOriginal.timestamp()))

def manually(img: Image, file_path: str, sr: os.stat_result, exif: Exif):
    while True:
        input_str = input("\n手動での日時登録を行いますか? \"v\"で画像を表示 (y/n/v) > ")
        if input_str == "y":
            while True:
                date_str = input("\n日時を例に従って入力してください。\"c\"でキャンセルできます。 (例: %s) > "%datetime.now().strftime("%Y:%m:%d %H:%M:%S"))
                try:
                    inputted_date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    if date_str == "c":
                        print("\nキャンセルされました。")
                        return
                    print("入力が正しくありません。")
                    continue
                break
            exif.change_datetime(inputted_date)
            save(img, file_path, sr, exif)
            print("登録しました。\n")
            break
        elif input_str == "n":
            print("\nキャンセルされました。")
            break
        elif input_str == "v":
            img.show()
        else:
            print("入力が正しくありません。")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--skip", help="Skip files for which datetime already exists", action="store_true")
    parser.add_argument("--start-from", help="Check Exif from specified numbered file.", type=int)
    parser.add_argument("--fix-modified-date", help="Set the modified date to the same as the date in the Exif.", action="store_true")
    args = parser.parse_args()
    return(args)

def handler(signal, frame):
        print("\n\nユーザにより中断されました。\n")
        sys.exit(0)

signal.signal(signal.SIGINT, handler)

if __name__ == "__main__":
    args = get_args()

    files = glob.glob(args.file)
    files = [s for s in files if os.path.splitext(s)[1] in {".jpg", ".jpeg", ".JPG", ".png", ".PNG"}]
    editted_file = []

    print()

    if not files:
        print("\n画像ファイルが見つかりません。\n")
        exit()
    
    n = args.start_from - 1 if not args.start_from is None else 0
    skip = args.skip
    fix_modified_date = args.fix_modified_date

    for file_path in files[n:]:
        print(str(n+1)+"/"+str(len(files)))
        print("ファイル名: "+os.
        path.basename(file_path))
        print("パス: "+file_path)

        modified_time: datetime = get_modified_time(file_path)
        print("更新日時: " + modified_time.strftime("%Y:%m:%d %H:%M:%S"))

        img: Image = Image.open(file_path)
        sr = os.stat(path = file_path)
        exif: Exif = get_exif(img)

        if exif.Exif_DateTimeOriginal is None:
            print("このファイルには日時情報がありません。")
            print("更新日時に基づいて、以下のExifを追加します。")
            print("\n\tExif_DateTimeOriginal: "+modified_time.strftime("%Y:%m:%d %H:%M:%S"))
            print("\tExif_OffsetTime: "+"+09:00")
            while True:
                input_str = input("\nよろしいですか? \"v\"で画像を表示 (y/n/v) > ")
                if input_str == "y":
                    exif.change_datetime(modified_time)
                    save(img, file_path, sr, exif)
                    print("登録しました。")
                    break
                elif input_str == "n":
                    manually(img, file_path, sr, exif)
                    break
                elif input_str == "v":
                    img.show()
                else:
                    print("入力が正しくありません。")
        
        else:
            print("このファイルにはすでに日時情報が存在します。")
            print("\nExif_DateTimeOriginal: "+str(exif.Exif_DateTimeOriginal))
            print("Exif_DateTimeDigitized: "+str(exif.Exif_DateTimeDigitized))
            print("Exif_OffsetTime: " + str(exif.Exif_OffsetTime))
            print("0th_DateTime: "+str(exif.zeroth_DateTime))
            if skip:
                print("\nスキップされました。")
            else:
                manually(img, file_path, sr, exif)
            if fix_modified_date:
                os.utime(path=file_path, times=(sr.st_atime, exif.Exif_DateTimeOriginal.timestamp()))
                print("Exifの日時を基に更新日時を変更しました。")

        print()
        n += 1

    print("全てのファイルに対する操作が完了しました。\n")