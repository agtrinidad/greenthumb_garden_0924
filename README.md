![DASHBOARD](https://github.com/user-attachments/assets/e9655510-7c5d-4a48-ab74-f94842dae450)
<p align=center> https://public.tableau.com/app/profile/agtrinidad/viz/GreenThumbCommunityGardens/DASHBOARD </p>

# greenthumb_garden_0924

This project explores data sourced from NYC OpenData's GreenThumb Garden Info, dated to 9/16/2024. Further updates are not reflected in this repo.
The most up-to-date version of this record [can be found on NYC OpenData's archive](https://data.cityofnewyork.us/dataset/GreenThumb-Garden-Info/p78i-pat6/about_data).

Additional data regarding Neighborhood Tabulation Areas was also provided by NYC OpenData. This dataset was called via API and is likewise available [through the OpenData archive](https://data.cityofnewyork.us/City-Government/2010-Neighborhood-Tabulation-Areas-NTAs-/cpf4-rkhq). Unlike GreenThumb Garden Info, this dataset is not actively updated. It should be noted that while GreenThumb Garden Info was updated as late as September 2024, it still used 2010 NTAs as reference.

The original, unaltered dataset is contained in an Excel-compatible CSV (GreenThumb_Garden_Info_20240916.csv).
The included notebook (greenthumb_garden_0924.ipynb) demonstrates Python-based data cleaning. A Python script version of the same is included (gtgarden_script.py).
Its output (greenthumb_garden_clean.csv) reflects the dataset post-processing.

The included Tableau workbook (greenthumb.twb) reflects this cleaned version of the available data. <br>
[An interactive version is hosted here, hosted on Tableau's website.](https://public.tableau.com/app/profile/agtrinidad/viz/GreenThumbCommunityGardens/DASHBOARD)

---------------------------------------------------------------------------------------------------------------

Established in 1978, GreenThumb is a program providing programming and support to over community gardens in New York City. The entity operates as part of the Department of Parks & Recreation. Before becoming gardens, many of the lots supported by Greenthumb had been vacant and abandoned. Local community volunteers gradually transformed these locations into spaces for socialization, relaxation, and urban agricultural development. Today, GreenThumb works with over 550 individual gardens across the city.

This project had two fundamental goals:
<br>a) Efficient and accurate Python-based data cleaning
<br>b) Visually appealing and effective dashboard creation

The end-product dashboard can be used to draw insights and identify gardens of interest.
