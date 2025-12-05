Welcome to my Photo Database Sorting Repository!

The 1st Goal Of this Codebase was to organize some photos, currently complete and available to the public!

I accomplished this with:
  1. Take a mess of photos and extract their metadata
  2. Generate an ID label based on metadata
  3. Copy Photo and rename with ID label
  4. Generate a CSV with columns: {date: "mm-dd-yyyy", time: "hh-mm-ss", original_filename: "orig_path", id: "yyyy-mm-dd-###"}

The 1st Goal was accomplished in photoOrganizerScript.py 

## ------------------------------------------------------------

New set of goals for this codebase: 
  1. Organize a much larger set of photos.
       - Specifically I want to organize a folder with a bunch of subfolders. From these Subfolders I want all images
             - excluding specific folders (my situation: Mystery, Chondrichthyes, Inverts, Fish_In)

  2. Create a Master CSV outside the folder
       - same columns from before 

  3. A New folder with all of the images relabeled with new ID (format "genus-yyyy-mm-dd-###")

  4. A second new folder with subfolders matching origina folder but with relabeled photos.

## ------------------------------------------------------------

  Additional Goals: 

  1. A scrape from messy datasource to match coordinates to dates

  2. API Call to match environmental conditions to coordinates
     - Satellite Clorophyll (the day average)
     - Wind
     - Temperature
     - Current Speed
     - other environmental conditions 

  
