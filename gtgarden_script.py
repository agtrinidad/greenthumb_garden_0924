# %%
#Basic dataframe & numerical libraries
import pandas as pd 

#Importing visualization libraries for exploratory analysis
import matplotlib.pyplot as plt 
import seaborn as sns 

#Importing to standardize formatting (geolocation)
import geopy

#Importing geocoder classes
from geopy.geocoders import GoogleV3

#This library (safetyfile) contains a Google Maps API key.
#It is excluded from the uploaded dataset in the interest of informational security.
import safetyfile
from safetyfile import googleapi

print(type(googleapi))

# %%
#Reading original CSV to dataframe
gtgarden = pd.read_csv('GreenThumb_Garden_Info_20240916.csv')
gtgarden.info()

# %%
#Looking at a limited sample of entries
gtgarden.sample(5)

# %%
#It looks like Pandas incorrectly read in ZIP Codes as floats...
#These function below should fix it.
def repairzip(textobj):
      return str(textobj).replace(',','')

# %%
#Let's put into action!
gtgarden['zipcode'] = gtgarden['zipcode'].apply(repairzip)
print(gtgarden['zipcode'].sample(5))

# %%
#Finding coordinates problem entries, slicing into separate DataFrame
#We can use 'lat' as a proxy for both latitude and longitude: when one is absent, the other is absent

slice = gtgarden[pd.isnull(gtgarden['lat'])].copy()
slice.info()

# %%
#Creating GoogleV3 class, searches using Google Map API to identify submitted addresses
#The aforementioned API key is used here.

geolocator = GoogleV3(api_key=googleapi)

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
#With that done, let's now join this content back into the main dataframe.
gtgarden.update(slice, overwrite=False, join='left', errors='ignore')
gtgarden.info()

# %%
#Just to double check... no null values!
gtgarden[gtgarden['lon'].isnull()]

# %%
#But we're seeing a problem with 'CensusTract'.
gtgarden[gtgarden['CensusTract'].isnull()].sample(5)

# %%
#While geopy doesn't have native support for US Census Geocoder API...
#A small package called 'censusgeocode' does.

import censusgeocode as cg

# %%
#Let's make another slice.
slice = gtgarden[gtgarden['CensusTract'].isnull()].copy()
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
#Return again to the main dataframe!
gtgarden.update(slice, overwrite=False, join='left', errors='ignore')
gtgarden.info()

# %%
#We see that some results still lack crossStreets: that is, intersections.
slice = gtgarden[gtgarden['crossStreets'].isna()].copy()
print(slice.sample(5))

#Unfortunately, Google's API doesn't support returning intersections.
#In some cases, identifiying intersections might be inappropriate.
#Given that we're cleaning this dataset for later visualization, this column isn't essential for user use.

#For now, we'll fill these with the string value 'N/A'.
#These can be updated with new values from an updated version of the sheet.

gtgarden['crossStreets'] = gtgarden['crossStreets'].fillna('N/A')

#We can, however, address some shorthand which might not show up well in our ultimate visualization.
gtgarden['crossStreets'] = gtgarden['crossStreets'].replace(r'[Bb][Tt][Ww][Nn]?', r'Between', regex=True)

# %%
#It still looks like we have some blank values here and there...
gtgarden.info()

# %%
#Column indices [9,15] are all describing open hours.
#A bit confusingly, they go in the order of: [Friday, Monday, Saturday, Sunday, Thursday, Tuesday, Wednesday].
#We can conver this to [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday] at a later point.

slice = gtgarden.iloc[:,9:16].copy()
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
#Back to the main dataframe.
gtgarden.update(slice, overwrite=True, join='left', errors='ignore')
gtgarden.info()

# %%
#Nice! Now let's clear away non-necessities...
gtgarden = gtgarden.map(lambda x: x.strip() if isinstance(x, str) else x)
gtgarden.sample(5)

# %%
#Let's sort the columns into a more logical order.
#We'll prioritize unique information, like name, address, and coordinates first.
#Status will also be prioritized.

#More categorical tags, like congressional districts, can be moved after them.
#We'll move open hours to the very back...

gtgarden = gtgarden[['parksid',
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

gtgarden.sample(5)

# %%
#One last thing! It's really weird that the boroughs are acronymized in this way...
#The good thing is that the creators of this dataset made every borough have a unique one-character symbol.
#We'll replace them with the function below:

def boroughsort(chara):
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
    
gtgarden['borough'] = gtgarden['borough'].apply(boroughsort)
gtgarden['borough'].sample(5)

# %%
#These are corrections to a few... small unique errors in the original dataset.
#For example, this garden in the Bronx being designated as Brooklyn.

print(gtgarden.loc[5,'gardenname'])
print(gtgarden.loc[5,'borough'])
gtgarden.loc[5, 'borough'] = 'Bronx'

#Easy fix.
#We've made this dataset usable, but it might take some more work than this to make it perfect.

# %%
#Still, though. This seems good enough to go!
#Let's output our new, cleaned, upgraded dataset.

gtgarden_postclean = gtgarden

# %%
#Write cleaned dataframe to CSV!
gtgarden_postclean.to_csv("greenthumb_garden_clean.csv", sep=',', encoding='utf-8', index=False)


