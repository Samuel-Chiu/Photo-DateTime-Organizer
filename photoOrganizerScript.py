from PIL import Image
from PIL.ExifTags import TAGS
from pathlib import Path
import cv2
import csv
import os


# Takes in: image folder path
# Returns: lists of images in the folder and their filenames
# Purpose: Load images from a specified folder for further processing

def load_images_from_folder(folder):

    ImageDict = {}

    images = []
    filenames = [] 
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)

        if os.path.isfile(filepath):
            img = cv2.imread(filepath)

            if img is not None:
                images.append(img)
                filenames.append(filepath)

                ImageDict[filepath] = img

    return (images, filenames, ImageDict)



# Takes in: image file path
# Returns: EXIF date information as a string
# Purpose: Extract date information from the EXIF metadata of an image, to be used before formatExifData

def extractExifDate(filePath):
    img = Image.open(filePath)
    exifdata = img.getexif()

    for tag_id in exifdata:
        tag_name = TAGS.get(tag_id, tag_id)

        if tag_name in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
            return f"{tag_name}: {exifdata.get(tag_id)}"
    
    return "No date information found in EXIF data."


# Takes in: extracted Exif data as a string
# Returns: processed date and time information as a list
# Purpose: Process the raw EXIF data to extract and format date and time information

def formatExifData(RawExifData):

    listDateTime = RawExifData.strip().split(" ")

    exifDate = listDateTime[1]
    exifTime = listDateTime[2]


    yearMonthDay = exifDate.strip().split(":")

    year = yearMonthDay[0]
    month = yearMonthDay[1]
    day = yearMonthDay[2]

    date = f"{year}-{month}-{day}"


    hourMinSec = exifTime.strip().split(":")

    hour = hourMinSec[0]
    min = hourMinSec[1]
    second = hourMinSec[2]

    time = f"{hour}-{min}-{second}"


    processedData = [date, time]

    return processedData




def saveCopy(img, output_path):
    cv2.imwrite(output_path, img)

#----------------------------------------------------------------------------------------------------
def main():
    
    script_dir = os.path.dirname(os.path.abspath(__file__))

    base_directory = script_dir

    for path, folders, files in os.walk(base_directory):
        for folder in folders:

            if folder.endswith("Sorted"):
                continue


            folder_name = f"{folder}"
            lowercaseName = folder_name.lower()

            image_folder = os.path.join(script_dir, folder_name)

            output_folder = os.path.join(script_dir, f"{lowercaseName}Sorted")
            os.makedirs(output_folder, exist_ok=True)



            (images, filenames, ImageDict) = load_images_from_folder(image_folder)


            print(f"Loaded {len(images)} images.")

            image_data = []

            for i in range(len(images)):
                img = images[i]
                path = filenames[i]


                rawExifData = extractExifDate(path)
                dateInfo = formatExifData(rawExifData)

                date = dateInfo[0]
                time = dateInfo[1]

                image_data.append({
                    "image": img,
                    "path": path,
                    "date": date,
                    "time": time
                })


            image_data.sort(key=lambda x: (x['date'], x['time']))

            IDs = []

            idNum = 0

            for imageDict in image_data:

                img = imageDict["image"]
                path = imageDict["path"]
                date = imageDict["date"]
                time = imageDict["time"]

                p = Path(path)
                original_filename = p.name

                imageDict["original_filename"] = original_filename

                idNum += 1

                if idNum < 10:
                    idFormat = "00" + str(idNum)

                elif 10 <= idNum < 100:
                    idFormat = "0" + str(idNum)

                else: 
                    idFormat= str(idNum)

                id = lowercaseName + "-" + date + "-" + idFormat

                imageDict["id"] = id

                output_path = os.path.join(output_folder, f"{id}.jpg")
                saveCopy(img, output_path)

                IDs.append(id)

                imageDict.pop("image")
                imageDict.pop("path")

            #print(IDs)
                
            #----------------------------------------------------------------------------------------------------

            fieldnames = ["date", "time", "original_filename", "id"]

            csv_filename = os.path.join(output_folder, f"{lowercaseName}_image_data.csv")

            with open(csv_filename, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()  # Write the header row
                writer.writerows(image_data)  # Write all data rows

            print(f"Data successfully written to {csv_filename}")

if __name__ == "__main__":
    main()

# --- IGNORE ---