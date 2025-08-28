#Importing necessary packages
import requests
from requests import get
import json
import re

#Basic DataFrame & numerical libraries
import pandas as pd 
#Importing visualization libraries for exploratory analysis
import matplotlib.pyplot as plt 
import seaborn as sns 
#Importing to standardize formatting (geolocation)
import geopy
#Importing geocoder classes
from geopy.geocoders import GoogleV3
#Logical conclusion of importing pandas and geopy
import shapely #will help us work with geocoded data later
from shapely.geometry import Point, Polygon

#This local library (safety_file) contains a Google Maps API key.
#It is excluded from the uploaded dataset in the interest of informational security.
import safety_file
from safety_file import GOOGLE_API

print(type(GOOGLE_API))

# %%
#Reading original CSV to DataFrame
gt_garden_df = pd.read_csv('GreenThumb_Garden_Info_20240916.csv')
gt_garden_df.info()

# %%
#Looking at a limited sample of entries
gt_garden_df.sample(5)

# %%
#It looks like Pandas incorrectly read in ZIP Codes as floats...
#These function below should fix it.
def repairzip(textobj):
      return str(textobj).replace(',','')

# %%
#Let's put into action!
gt_garden_df['zipcode'] = gt_garden_df['zipcode'].apply(repairzip)
print(gt_garden_df['zipcode'].sample(5))

# %%
#Finding coordinates problem entries, slicing into separate DataFrame
#We can use 'lat' as a proxy for both latitude and longitude: when one is absent, the other is absent

slice = gt_garden_df[pd.isnull(gt_garden_df['lat'])].copy()
slice.info()

# %%
#Creating GoogleV3 class, searches using Google Map API to identify submitted addresses
#The aforementioned API key is used here.

geolocator = GoogleV3(api_key=GOOGLE_API)

# %%
#Using .apply() to basically create a Google Maps query for the address
#Some addresses lack building numbers: adding in the garden name AND ZIP Code gets around this problem
slice['pseudoaddress'] = slice.apply(lambda row: f'{row['gardenname']} {row['address']} {row['zipcode']}', axis = 1)

# %%
#Extracting geocodes relevant to each item...
slice['geocode'] = slice['pseudoaddress'].apply(lambda x: geolocator.geocode(x))

#This returns a geocode inherently incorporating both latitude and longitude
#On the off-chance a location is not on Google Maps, however, it might return 'None' instead

# %%
#And applying back as necessary...
def gc_lat(geocode):
    try:
        return geocode.latitude
    except AttributeError as err:
        return None
    
def gc_lon(geocode):
    try:
        return geocode.longitude
    except AttributeError as err:
        return None

slice['lat'] = slice['geocode'].apply(gc_lat).astype('float')
slice['lon'] = slice['geocode'].apply(gc_lon).astype('float')

# %%
#It turns out that there's a singular row in which the Google API was unable to determine its location...
#At index 130 is the "South Beach community garden NYCHA" at 100 Kramer street 10306.
#It's entirely unindexed by Google Maps. We do still have a standard address.
#We can clean this one up manually.

slice.loc[130, 'lat'] = gc_lat( geolocator.geocode(slice.loc[130, 'address']) )
slice.loc[130, 'lon'] = gc_lon( geolocator.geocode(slice.loc[130, 'address']) )

#Some other addresses only state the street name in ALL CAPS rather than the address.
#Google Maps, based on the provided information, is still able to approximate these locations.

# %%
#Let's drop the added column "pseudoaddress" now that we no longer need it...
slice = slice.drop(columns=['geocode'])

# %%
#With that done, let's now join this content back into the main DataFrame.
gt_garden_df.update(slice, overwrite=False, join='left', errors='ignore')
gt_garden_df.info()

# %%
#Just to double check... no null values!
gt_garden_df[gt_garden_df['lon'].isnull()]

# %%
#But we're seeing a problem with 'CensusTract'.
gt_garden_df[gt_garden_df['CensusTract'].isnull()].sample(5)

# %%
#While geopy doesn't have native support for US Census Geocoder API...
#A small package called 'censusgeocode' does.

import censusgeocode as cg

# %%
#Let's make another slice.
slice = gt_garden_df[gt_garden_df['CensusTract'].isnull()].copy()
slice.sample(5)['CensusTract']

# %%
#defining a function that can be used with apply
def extractcensustract(row):
    inlat = row['lat']
    inlon = row['lon']
    resultobj = cg.coordinates(x=inlon, y=inlat, returntype='geographies')
    tract = resultobj['Census Tracts'][0]['TRACT']
    tract = float(tract[:4]+"."+tract[4:])
    return tract

#Census tracts can either be expressed as a 6 digit code or as a float:
    #That is, tract 57.02 can be written as 005702 and vice versa.
    #For the purposes of this cleaning, we're converting all tracts into floats.
    #Actually, this makes them easier to find: most public resources use their float identity.

#Example
extractcensustract(slice.sample(1))

# %%
#Applying the function to the slice
slice['CensusTract'] = slice.apply(extractcensustract, axis=1)
slice[['address','CensusTract','lat','lon']].sample(5)

# %%
#Return again to the main DataFrame!
gt_garden_df.update(slice, overwrite=False, join='left', errors='ignore')
gt_garden_df.info()

# %%
#We see that some results still lack crossStreets: that is, intersections.
slice = gt_garden_df[gt_garden_df['crossStreets'].isna()].copy()
print(slice.sample(5))

#Unfortunately, Google's API doesn't support returning intersections.
#In some cases, identifiying intersections might be inappropriate.
#Given that we're cleaning this dataset for later visualization, this column isn't essential for user use.

#For now, we'll fill these with the string value 'N/A'.
#These can be updated with new values from an updated version of the sheet.

gt_garden_df['crossStreets'] = gt_garden_df['crossStreets'].fillna('N/A')

#We can, however, address some shorthand which might not show up well in our ultimate visualization.
gt_garden_df['crossStreets'] = gt_garden_df['crossStreets'].replace(r'[Bb][Tt][Ww][Nn]?', r'Between', regex=True)

# %%
#It still looks like we have some blank values here and there...
gt_garden_df.info()

# %%
#Column indices [9,15] are all describing open hours.
#A bit confusingly, they go in the order of: [Friday, Monday, Saturday, Sunday, Thursday, Tuesday, Wednesday].
#We can conver this to [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday] at a later point.

slice = gt_garden_df.iloc[:,9:16].copy()
slice.sample(15)

# %%
#There seem to be some tiny errors...
slice[slice=='close'].count()

#For example, instances of having written "close" or "Close" or even "Closed" as opposed to standard "CLOSED".
#This is an easy fix.

# %%
#This regex searches for any variation on "CLOSED", D-optional, and replace them with "CLOSED".
slice = slice.replace(r'[Cc][Ll][Oo][Ss][Ee][dD]?','CLOSED', regex=True)

# %%
#There's still tiny inconsistencies like how some entries include "a" or "p" in place of "a.m." or "p.m."
#We can also fix that easily.

slice.sample(15)

# %%
#Correcting single character formatting
slice = slice.replace(r'(\d*:?\d*)([Aa])(\s)','\\1 a.m.\\3',regex=True)
slice = slice.replace(r'(\d*:?\d*)([Aa])(\s?$)','\\1 a.m.\\3',regex=True)
slice = slice.replace(r'(\d*:?\d*)([Pp])(\s)','\\1 p.m.\\3',regex=True)
slice = slice.replace(r'(\d*:?\d*)([Pp])(\s?$)','\\1 p.m.\\3',regex=True)

#Eliminating inconsistent spacing and stray numerals
slice = slice.replace(r'([1-9])(:)([Pp])','\\1:00 \\3',regex=True)
slice = slice.replace(r'([1-9])(:)([Aa])','\\1:00 \\3',regex=True)
slice = slice.replace(r'^([1-9]?[1-9])(:)?\s*([Pp])','\\1:00 \\3',regex=True)
slice = slice.replace(r'^([1-9]?[1-9])(:)?\s*([Aa])','\\1:00 \\3',regex=True)

#General consistency
slice = slice.replace(r'[Aa].?[Mm].?','a.m.', regex=True)
slice = slice.replace(r'[Pp].?[Mm].?','p.m.', regex=True)
slice = slice.replace(r'-','to', regex=True)
slice = slice.replace(r'Noon','12:00 p.m.', regex=True)
slice = slice.replace(r'.-', ' -', regex=True)
slice = slice.replace(r'\s?(:)\s?',':',regex=True)
slice = slice.replace(r'(\w)(to)(\w)',r'\1 to \3', regex=True)


#Dealing with lists
slice = slice.replace(r'\s?(,|&|;)(\s*)(\d)',r';\n\3', regex=True)


slice.sample(15)

# %%
#Unlike latitude or longitude, we can't extrapolate other information to fill these times.
#It's probably not appropriate to assume that they're closed during unlisted times either...

#Pending further updates on the original sheet, we can fill these with a 'N/A' label.

#There's data-original oddities like 'Sunset to Sundown' at '955 Columbus Avenue'.
#It might best to leave these alone: again, there's not other information to extrapolate from for proper corrections.

slice = slice.fillna('N/A')
slice.sample(15)

# %%
#Back to the main DataFrame.
gt_garden_df.update(slice, overwrite=True, join='left', errors='ignore')
gt_garden_df.info()

# %%
#Nice! Now let's clear away non-necessities...
gt_garden_df = gt_garden_df.map(lambda x: x.strip() if isinstance(x, str) else x)
gt_garden_df.sample(5)

# %%
#Let's sort the columns into a more logical order.
#We'll prioritize unique information, like name, address, and coordinates first.
#Status will also be prioritized.

#More categorical tags, like congressional districts, can be moved after them.
#We'll move open hours to the very back...

gt_garden_df = gt_garden_df[['parksid',
                    'gardenname',
                    'status',
                    'address',
                    'lat',
                    'lon',
                    'BBL',
                    'borough',
                    'crossStreets',
                    'zipcode',
                    'openhrsm',
                    'openhrstu',
                    'openhrsw',
                    'openhrsth',
                    'openhrsf',
                    'openhrssa',
                    'openhrssu',
                    'CensusTract',
                    'assemblydist',
                    'communityboard',
                    'NTA',
                    'congressionaldist',
                    'coundist',
                    'statesenatedist',
                    'policeprecinct',
                    'juris',
                    'multipolygon']]

gt_garden_df.sample(5)

# %%
#It's really weird that the boroughs are acronymized in this way...
#The good thing is that the creators of this dataset made every borough have a unique one-character symbol.
#We'll replace them with the function below:

def borough_sort(chara):
    if chara == 'M':
        return 'Manhattan'
    elif chara == 'X':
        return 'Bronx'
    elif chara == 'B':
        return 'Brooklyn'
    elif chara == 'Q':
        return 'Queens'
    else:
        return 'Staten Island'
    
gt_garden_df['borough'] = gt_garden_df['borough'].apply(borough_sort)
gt_garden_df['borough'].sample(5)

# %%
#These are corrections to a few... small unique errors in the original dataset.
#For example, this garden in the Bronx being des.ignated as Brooklyn.

print(gt_garden_df.loc[5,'gardenname'])
print(gt_garden_df.loc[5,'borough'])
gt_garden_df.loc[5, 'borough'] = 'Bronx'

#Easy fix.
#We've made this dataset usable, but it might take some more work than this to make it perfect.

# %%
#It'll be nice if we can sort these by neighborhood.
#These records include NTA (Neighborhood Tabulation Areas), but unfortunately these only contain the serial codes.
#Some of these are still missing, too... The ones present are based on the 2010 NTAs.
#First, let's import the NTA table as a DataFrame.

ntatableraw = get("https://data.cityofnewyork.us/resource/q2z5-ai38.json").json()
ntarecords = pd.DataFrame(ntatableraw)
ntarecords.info()

ntarecords.sample(5)

# %%
#Let's transform those geometries into multipolygon shapes.
#What we're trying to do is check if these points are in these multipolygons...
ntarecords['the_geom'] = ntarecords['the_geom'].apply(lambda x: dict(x))
ntarecords['the_geom'] = ntarecords['the_geom'].apply(lambda x: shapely.geometry.shape(x))
ntarecords['the_geom'].sample(4)

#Great!

# %%
#Cool! Now let's clean the NTA column in 'gt_garden_df'.

gt_garden_df['NTA'] = gt_garden_df['NTA'].apply(lambda x: x[:4])
gt_garden_df['NTA'].sample(3)

# %%
#We still have to take care of those empty 'NTA' rows...
#The 'slice' is back!

slice = gt_garden_df[gt_garden_df['NTA'] == '/'].copy()
slice.sample(5)

# %%
#For our own ease, let's make some "Points" in this isolated DataFrame
slice['Points'] = slice.apply(lambda row: Point(row['lon'],row['lat']), axis=1)
slice['Points'].sample(5)

# %%
#Now, let's try and apply this...

def find_nta(point):
    for instance, row in ntarecords.iterrows():
        if row['the_geom'].contains(point):
            return row['ntacode']
    return None

slice['NTA'] = slice['Points'].apply(lambda x: find_nta(x))
slice['NTA'].sample(5)

#Success!

# %%
#Let's put things back where they were.
gt_garden_df.update(slice, overwrite=True, join='left', errors='ignore')
gt_garden_df.info()

# %%
#Let's crosscheck these objects again.
def nbcrosscheck(nta):
    for instance, row in ntarecords.iterrows():
        if row['ntacode'] == nta:
            return row['ntaname'] #Essentially the same as checking which polygons fell where
            break
    return None

gt_garden_df['neighborhood'] = gt_garden_df['NTA'].apply(nbcrosscheck)
gt_garden_df['neighborhood'].sample(5)

# %%
#Let's put things back in order.
gt_garden_df = gt_garden_df[['parksid',
                    'gardenname',
                    'status',
                    'address',
                    'lat',
                    'lon',
                    'BBL',
                    'neighborhood',
                    'borough',
                    'crossStreets',
                    'zipcode',
                    'openhrsm',
                    'openhrstu',
                    'openhrsw',
                    'openhrsth',
                    'openhrsf',
                    'openhrssa',
                    'openhrssu',
                    'CensusTract',
                    'assemblydist',
                    'communityboard',
                    'NTA',
                    'congressionaldist',
                    'coundist',
                    'statesenatedist',
                    'policeprecinct',
                    'juris',
                    'multipolygon']]

# %%
#Great! Now let's also rename these so they're more useful for us.
#First, let's set everything to CamelCase. We'll also unshorten and deacronymize names.
#In the case of the hours, we'll rename them for the sake of clarity.

gt_garden_df.rename(columns={   'parksid':'ParkID',
                    'gardenname':'GardenName',
                    'status':'Status',
                    'address':'Address',
                    'lat':'Latitude',
                    'lon':'Longitude',
                    'BBL':'BoroughBlockLot',
                    'neighborhood':'Neighborhood',
                    'borough':'Borough',
                    'crossStreets':'CrossStreets',
                    'zipcode':'ZIPCode',
                    'openhrsm':'MondayHours',
                    'openhrstu':'TuesdayHours',
                    'openhrsw':'WednesdayHours',
                    'openhrsth':'ThursdayHours',
                    'openhrsf':'FridayHours',
                    'openhrssa':'SaturdayHours',
                    'openhrssu':'SundayHours',
                    'CensusTract':'CensusTract',
                    'assemblydist':'AssemblyDistrict',
                    'communityboard':'CommunityBoard',
                    'NTA':'NeighborhoodTabulationArea',
                    'congressionaldist':'CongressionalDistrict',
                    'coundist':'CityCouncilDistrict',
                    'statesenatedist':'StateSenateDistrict',
                    'policeprecinct':'PolicePrecinct',
                    'juris':'Jurisdiction',
                    'multipolygon':'MultipolygonShape'
                },  
                inplace=True    )

gt_garden_df.info()

# %%
#One last thing...
#Let's standardize street names in the addresses.
#Specifically: we want to target those capitalizations.

def titlecase(address):
    return re.sub(r'([A-Z]{3,})', lambda x: x.group(0).title(), address) 

#This one was a little hard to figure out
#Specifically using 3 or more here to make sure naming conventions with successive capital letters are unaffected
#Didn't use blanket .title() method to respect Irish names (among others)

gt_garden_df['Address'] = gt_garden_df['Address'].apply(titlecase)

# %%
#This seems good enough to go!
#Let's output our new, cleaned, upgraded dataset.

gt_garden_df_postclean = gt_garden_df

# %%
#Write cleaned DataFrame to CSV!
gt_garden_df_postclean.to_csv("greenthumb_garden_clean.csv", sep=',', encoding='utf-8', index=False)




