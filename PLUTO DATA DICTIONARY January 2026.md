PLUTO DATA DICTIONARY January 2026 (25v4) 
 
1 
 
Table of Contents 
 
DISCLAIMER ............................................................................................................................................... 3 
INTRODUCTION ......................................................................................................................................... 3 
BOROUGH  (Borough) ................................................................................................................................. 4 
TAX BLOCK  (Block) .................................................................................................................................. 4 
TAX LOT  (Lot) ............................................................................................................................................ 4 
COMMUNITY DISTRICT  (CD) ................................................................................................................. 5 
CENSUS TRACT 2020 (BCT2020) ............................................................................................................. 6 
CENSUS BLOCK 2020 (BCTCB2020) ........................................................................................................ 7 
CENSUS TRACT 2010 (CT2010) ................................................................................................................ 8 
CENSUS BLOCK 2010 (CB2010) ............................................................................................................... 8 
SCHOOL DISTRICT  (SchoolDist) .............................................................................................................. 9 
CITY COUNCIL DISTRICT  (Council) ....................................................................................................... 9 
ZIP CODE  (ZipCode) ................................................................................................................................. 10 
FIRE COMPANY  (FireComp) ................................................................................................................... 10 
POLICE PRECINCT  (PolicePrct) .............................................................................................................. 10 
HEALTH CENTER DISTRICT (HealthCenterDist) .................................................................................. 11 
HEALTH AREA (HealthArea) ................................................................................................................... 11 
SANITATION DISTRICT BORO (SanitBoro) .......................................................................................... 12 
SANITATION DISTRICT NUMBER (SanitDist) ..................................................................................... 12 
SANITATION SUBSECTION (SanitSub) ................................................................................................. 12 
ADDRESS  (Address) ................................................................................................................................. 13 
ZONING DISTRICT 1  (ZoneDist1) .......................................................................................................... 13 
ZONING DISTRICT 2  (ZoneDist2) .......................................................................................................... 14 
ZONING DISTRICT 3  (ZoneDist3) .......................................................................................................... 14 
ZONING DISTRICT 4  (ZoneDist4) .......................................................................................................... 15 
COMMERCIAL OVERLAY 1  (Overlay1) ................................................................................................ 15 
COMMERCIAL OVERLAY 2  (Overlay2) ................................................................................................ 16 
SPECIAL PURPOSE DISTRICT 1  (SPDist1) ........................................................................................... 16 
SPECIAL PURPOSE DISTRICT 2  (SPDist2) ........................................................................................... 17 
SPECIAL PURPOSE DISTRICT 3  (SPDist3) ........................................................................................... 17 
LIMITED HEIGHT DISTRICT  (LtdHeight) ............................................................................................. 18 
SPLIT BOUNDARY INDICATOR  (SplitZone)........................................................................................ 18 
BUILDING CLASS  (BldgClass) ............................................................................................................... 18 
LAND USE CATEGORY  (LandUse) ........................................................................................................ 19 
NUMBER OF  EASEMENTS (Easements) ................................................................................................ 20 
TYPE OF OWNERSHIP CODE  (OwnerType) ......................................................................................... 20 
OWNER NAME  (OwnerName) ................................................................................................................. 21 
LOT AREA  (LotArea) ................................................................................................................................ 21 
TOTAL BUILDING FLOOR AREA (BldgArea) ....................................................................................... 22 
COMMERCIAL FLOOR AREA (ComArea) ............................................................................................. 23 
RESIDENTIAL FLOOR AREA (ResArea) ................................................................................................ 24 
OFFICE FLOOR AREA (OfficeArea) ........................................................................................................ 24 
RETAIL FLOOR AREA (RetailArea) ........................................................................................................ 25 
GARAGE FLOOR AREA (GarageArea) .................................................................................................... 25 
STORAGE FLOOR AREA (StrgeArea) ..................................................................................................... 26 
FACTORY FLOOR AREA (FactryArea) ................................................................................................... 26 
OTHER FLOOR AREA (OtherArea) ......................................................................................................... 27 
TOTAL BUILDING FLOOR AREA SOURCE CODE  (AreaSource) ...................................................... 27 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
2 
 
NUMBER OF BUILDINGS (NumBldgs)................................................................................................... 28 
NUMBER OF FLOORS (NumFloors) ........................................................................................................ 28 
RESIDENTIAL UNITS (UnitsRes) ............................................................................................................ 29 
TOTAL UNITS (UnitsTotal) ....................................................................................................................... 29 
LOT FRONTAGE  (LotFront) .................................................................................................................... 29 
LOT DEPTH  (LotDepth) ............................................................................................................................ 30 
BUILDING FRONTAGE  (BldgFront)....................................................................................................... 30 
BUILDING DEPTH  (BldgDepth) .............................................................................................................. 30 
EXTENSION CODE  (Ext) ......................................................................................................................... 30 
PROXIMITY CODE  (ProxCode)............................................................................................................... 31 
IRREGULAR LOT CODE  (IrrLotCode) ................................................................................................... 31 
LOT TYPE   (LotType) ............................................................................................................................... 31 
BASEMENT TYPE/GRADE  (BsmtCode) ................................................................................................ 32 
ASSESSED LAND VALUE (AssessLand) ................................................................................................ 33 
ASSESSED TOTAL VALUE (AssessTot) ................................................................................................. 34 
EXEMPT TOTAL VALUE (ExemptTot) ................................................................................................... 34 
YEAR BUILT  (YearBuilt) ......................................................................................................................... 35 
YEAR ALTERED 1  (YearAlter1) .............................................................................................................. 35 
YEAR ALTERED 2  (YearAlter2) .............................................................................................................. 36 
HISTORIC DISTRICT NAME  (HistDist) ................................................................................................. 36 
LANDMARK STATUS  (Landmark) ......................................................................................................... 36 
BUILT FLOOR AREA RATIO (BuiltFAR) ............................................................................................... 36 
MAXIMUM ALLOWABLE RESIDENTIAL FAR  (ResidFAR).............................................................. 37 
MAXIMUM ALLOWABLE COMMERCIAL FAR  (CommFAR)........................................................... 37 
MAXIMUM ALLOWABLE COMMUNITY FACILITY FAR  (FacilFAR) ............................................ 38 
BORO CODE  (BoroCode) ......................................................................................................................... 38 
BOROUGH, TAX BLOCK & LOT (BBL) ................................................................................................ 39 
CONDOMINIUM NUMBER  (CondoNo) ................................................................................................. 39 
CENSUS TRACT 2  (Tract2010) ................................................................................................................ 39 
X COORDINATE  (XCoord) ...................................................................................................................... 40 
Y COORDINATE  (YCoord) ...................................................................................................................... 40 
ZONING MAP #  (ZoneMap) ..................................................................................................................... 41 
ZONING MAP CODE  (ZMCode) ............................................................................................................. 41 
SANBORN MAP #  (Sanborn).................................................................................................................... 41 
TAX MAP #  (TaxMap) .............................................................................................................................. 41 
E-DESIGNATION NUMBER  (EDesigNum) ............................................................................................ 42 
APPORTIONMENT BBL (APPBBL) ........................................................................................................ 42 
APPORTIONMENT DATE (APPDate) ..................................................................................................... 42 
PLUTO – DTM BASE MAP INDICATOR  (PLUTOMapID) ................................................................... 43 
2007 FLOOD INSURANCE RATE MAP INDICATOR (FIRM07_Flag)) ............................................... 43 
2015 PRELIMINARY FLOOD INSURANCE RATE MAP INDICATOR (PFIRM15_Flag) .................. 44 
VERSION NUMBER (Version).................................................................................................................. 44 
CHANGED BY DCP (DCPEdited)............................................................................................................. 44 
LATITUDE (Latitude) ................................................................................................................................. 45 
LONGITUDE (Longitude) .......................................................................................................................... 45 
NOTES (Notes) ........................................................................................................................................... 45 
APPENDIX A:  SPECIAL PURPOSE DISTRICTS................................................................................... 44 
APPENDIX B:  LIMITED HEIGHT DISTRICTS ..................................................................................... 47 
APPENDIX C:  BUILDING CLASS CODES ............................................................................................ 48 
APPENDIX D:  LAND USE CATEGORIES ............................................................................................. 52 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
DISCLAIMER 
PLUTO is provided by the Department of City Planning (DCP) on DCP’s website for informational 
purposes only.  DCP does not warranty the completeness, accuracy, content, or fitness for any particular 
purpose or use of PLUTO, nor are any such warranties to be implied or inferred with respect to PLUTO 
as furnished on the website. 
DCP and the City are not liable for any deficiencies in the completeness, accuracy, content, or fitness for 
any particular purpose or use of PLUTO, or applications utilizing PLUTO, provided by any third party. 
INTRODUCTION  
The PLUTO Data Dictionary defines the fields in the PLUTO file and the MapPLUTO geofiles in order 
of the field's position in the data file. 
The Data Dictionary contains the following: 
• Field Name: 
Two types of field names are included - external and internal field names. 
The external field name is the common name of the field. 
The internal field name, which appears in parenthesis, is the name of the field as defined 
in PLUTO. 
• Format: 
The format describes the type of field and the size of the field.  
There are two different types of fields, alphanumeric and numeric. In PLUTO, the 
alphanumeric fields can contain any combination of alphabetic letters, numbers, and 
special characters such as hyphens. Numeric fields only contain numbers. In 
MapPLUTO, the alphanumeric fields are text fields and the numeric fields may be of 
type double, long integer, or short integer. Note that fields that are blank in PLUTO 
contain a null value in the ESRI MapPLUTO geofiles. 
For alphanumeric fields, the size of the field is the size of the text field in MapPLUTO. 
For numeric fields, it is the expected maximum number of digits. 
• Data Source: 
The data source identifies the city agency and computer file or system from which the 
field was obtained or derived. 
• Description: 
3 
 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
4 
 
 
The description includes a brief explanation of the field and, where pertinent, the valid 
values for the field and examples. 
Field Name: BOROUGH  (Borough) 
 
Format: Alphanumeric - 2 characters 
 
Data Source: Department of City Planning - based on data from: 
Department of Finance - Property Tax System (PTS) 
 
Description: The borough in which the tax lot is located. 
 
This field contains a two-character borough code. 
 
Value Description 
BX Bronx 
BK Brooklyn 
MN Manhattan 
QN Queens 
SI Staten Island 
 
Two portions of the city, Marble Hill and Rikers Island, are legally located in one 
borough but are serviced by a different borough. The BOROUGH codes associated 
with these areas are the boroughs in which they are legally located. 
 
Marble Hill is serviced by the Bronx, but is legally located in Manhattan and has a 
BOROUGH of MN. Rikers Island is serviced by Queens, but is legally located in the 
Bronx and has a BOROUGH of BX. 
 
 
Field Name: TAX BLOCK  (Block) 
 
Format: Numeric - 5 digits (99999) 
 
Data Source: Department of Finance - Property Tax System (PTS) 
 
Description: The tax block in which the tax lot is located. 
 
This field contains a one to five-digit tax block number. 
 
Each tax block is unique within a borough (see BOROUGH). 
 
 
 
Field Name: TAX LOT  (Lot) 
 
Format: Numeric - 4 digits (9999) 
 
Data Source: Department of Finance - Property Tax System (PTS) 
 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
The number of the tax lot. 
This field contains a one to four-digit tax lot number. 
Each tax lot is unique within a tax block (see TAX BLOCK). 
Special handling for condominiums: 
In a condominium complex, each condominium unit is a separate tax lot and has its 
own lot number. In a residential condominium, the condominium units are generally 
the individual apartments; in a commercial condominium, the units might be floors in 
an office building, individual retail shops, or blocks of office space. These unit lot 
numbers have values between 1001 – 6999.  
Each unit tax lot has an associated billing lot number, with values between 7501 – 
7599. Lots in a condominium complex on the same block will have the same billing 
lot number. To make condominium information more compatible with parcel 
information, the Department of City Planning aggregates condominium unit tax lot 
information to the billing lot. For example, if a residential condominium building 
contains 20 units, the Department of Finance will assign 20 unit lot numbers and each 
of these lot numbers will have the same billing lot number. PLUTO will contain one 
record with the billing lot number and RESIDENTIAL UNITS will be set to 20. 
If the Department of Finance has not yet assigned a billing lot number to the 
condominium complex, PLUTO uses the lowest unit lot number within the complex. 
Note on MapPLUTO: The Department of Finance Digital Tax Map (DTM) contains 
the geography of the base lot for condominiums. The base lot is also called the 
“Formerly Known As” or FKA lot. For most condominium complexes, there is one 
base lot per billing lot. In using the DTM to create MapPLUTO, DCP replaces the 
base lot number with the billing lot number. If there is more than one base lot with the 
same billing lot number, DCP merges the base lots to create a geography for the 
billing lot.  
Under certain circumstances, DCP is unable to aggregate condominium unit tax lot 
information to the billing lot or to the lowest unit lot number. This occurs when a 
CONDOMINIUM NUMBER has not yet been assigned to the unit lots in PTS. In 
most cases, these unit lots will appear in PLUTO and in the NOT_MAPPED_LOTS 
table that is released with MapPLUTO. Before including these unit lots, the 
data is checked to verify that it pertains only to the unit lot. If unit lots have an 
identical address and a value for RESIDENTIAL UNITS that is greater than 1 and the 
same for all records, and there is no matching BBL in the DTM, they are assumed to 
part of the same condominium. BUILDING AREA is checked in the same way. These 
unit lots are removed from PLUTO and NOT_MAPPED_LOTS to avoid 
overcounting the number of residential units and building area. 
COMMUNITY DISTRICT  (CD) 
Numeric - 3 digits (999) 
5 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
6 
 
Data Source: Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
 
Description: The community district (CD) or joint interest area (JIA) for the tax lot. The city is 
divided into 59 community districts and 12 joint interest areas, which are large parks 
or airports that are not considered part of any community district. 
 
This field consists of three digits, the first of which is the borough code (see BORO 
CODE). The second and third digits are the community district or joint interest area 
number, whichever is applicable. 
 
Joint interest areas: 
 
BOROUGH  JIA NAME 
Manhattan 164 Central Park 
   
Bronx 
226 Van Cortlandt Park 
227 Bronx Park 
228 Pelham Bay Park 
   
Brooklyn 355 Prospect Park 
356 Gateway National Recreation Area 
   
Queens 
480 LaGuardia Airport 
481 Flushing Meadow/Corona Park 
482 Forest Park 
483 JFK International Airport 
484 Gateway National Recreation Area 
   
Staten Island 595 Gateway National Recreation Area 
 
Two portions of the city, Marble Hill and Rikers Island, are legally located in one 
borough, but serviced by a different borough.  The COMMUNITY DISTRICT 
associated with these areas is the community district by which they are serviced. 
 
Marble Hill is legally located in Manhattan, but is serviced by the Bronx and is 
divided between community districts 207 and 208. Rikers Island is legally located in 
the Bronx, but is serviced by Queens and is part of community district 401. 
 
COMMUNITY DISTRICT contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, COMMUNITY 
DISTRICT is calculated spatially using the tax lot’s XY COORDINATES and DCP’s 
Administrative District Base Map files. 
 
 
Field Name: CENSUS TRACT 2020 (BCT2020) 
 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Alphanumeric - 7 characters 
Department of City Planning – Geosupport System     
Department of City Planning – Administrative District Base Map files 
The 2020 census tract in which the tax lot is located. 
This field contains a seven-digit code representing the one-digit borough code 
followed by the six-digit census tract number. 
2020 census tracts are geographic areas defined by the U.S. Census Bureau for the 
2020 Census. Census tracts are comprised of census blocks. 
Each census tract is unique within a borough (see BOROUGH). 
Examples: 
Census Tract 4062600 
Census Tract 4063200 
CENSUS TRACT 2020 contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, CENSUS 
TRACT 2020 is calculated spatially using the tax lot’s XY COORDINATES and 
DCP’s Administrative District Base Map files. 
CENSUS BLOCK 2020 (BCTCB2020) 
Alphanumeric - 11 characters 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The 2020 census block in which the tax lot is located. 
This field contains an eleven-digit code representing the one-digit borough code 
followed by the six-digit census tract number and then the four-digit census block 
number.  
2020 census blocks are the smallest geographic areas defined by the U.S. Census 
Bureau. 
Each census block number is unique within a census tract (see CENSUS TRACT). 
Examples: 
Census Block 20350001000 
Census Block 30403001002 
CENSUS BLOCK 2020 contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, CENSUS 
BLOCK 2020 is calculated spatially using the tax lot’s XY COORDINATES and 
DCP’s Administrative District Base Map files. 
7 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
CENSUS TRACT 2010 (CT2010) 
Alphanumeric - 7 characters 
Department of City Planning – Geosupport System     
Department of City Planning – Administrative District Base Map files 
The 2010 census tract in which the tax lot is located. 
This field contains a one to four-digit census tract number, sometimes with a decimal 
point and a two-digit suffix.   
2010 census tracts are geographic areas defined by the U.S. Census Bureau for the 
2010 Census. Census tracts are comprised of census blocks. 
Each census tract is unique within a borough (see BOROUGH). 
Examples: 
Census Tract 203.01  
Census Tract 23  
CENSUS TRACT 2010 contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, CENSUS 
TRACT 2010 is calculated spatially using the tax lot’s XY COORDINATES and 
DCP’s Administrative District Base Map files. 
CENSUS BLOCK 2010 (CB2010) 
Alphanumeric - 5 characters 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The 2010 census block in which the tax lot is located. 
This field contains a four-digit census block number and, when applicable, a one
character alphabetic suffix.  
2010 census blocks are the smallest geographic areas defined by the U.S. Census 
Bureau. 
Each census block number is unique within a census tract (see CENSUS TRACT). 
Examples: 
Census Block 101A  
Census Block 102  
8 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
CENSUS BLOCK 2010 contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, CENSUS 
BLOCK 2010 is calculated spatially using the tax lot’s XY COORDINATES and 
DCP’s Administrative District Base Map files. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source:  
Description: 
SCHOOL DISTRICT  (SchoolDist) 
Alphanumeric - 2 characters 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The school district in which the tax lot is located. 
This field contains a two-digit school district number, which is preceded with a zero 
when the district number is one digit. 
The city is divided up into 34 school districts. Those districts are then divided into 
smaller zones which determine the area served by local schools. Each district has its 
own superintendent and receives guidance from a Community District Education 
Council made up of parents and local representatives.  
SCHOOL DISTRICT contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, SCHOOL 
DISTRICT is calculated spatially using the tax lot’s XY COORDINATES and DCP’s 
Administrative District Base Map files. 
CITY COUNCIL DISTRICT  (Council) 
Numeric - 2 digits (99) 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The city council district in which the tax lot is located. 
This field contains a two-digit city council district number, which is preceded with a 
zero when the district number is one digit. 
There are currently 51 city council districts in the City, which serve as political 
districts for the legislative branch of city government. 
. 
9 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
ZIP CODE  (ZipCode) 
Alphanumeric - 5 characters 
Department of City Planning – Geosupport System 
A ZIP code that is valid for one of the addresses assigned to the tax lot. 
Note that a tax lot may have multiple addresses and these addresses may not have the 
same ZIP code. A building with entrances on two streets may have a different ZIP 
code for each street address. ZIP CODE may not be valid for the street address in 
ADDRESS. 
If a tax lot does not have an ADDRESS or the ADDRESS contains a street name 
without a house number, ZIP CODE will be blank. 
FIRE COMPANY  (FireComp) 
Alphanumeric - 4 characters    
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files  
The fire company that services the tax lot. 
This field consists of four characters, the first of which is an alphabetic code 
identifying the type of fire company, where E stands for Engine, L stands for Ladder 
and Q stands for Squad.  The type code is followed by a one to three- digit fire 
company number which is preceded with leading zeros if the company number is less 
than three digits. 
FIRE COMPANY contains the value returned by Geosupport for one of the addresses 
assigned to the lot. If Geosupport does not return a value, FIRE COMPANY is 
calculated spatially using the tax lot’s XY COORDINATES and DCP’s 
Administrative District Base Map files. 
POLICE PRECINCT  (PolicePrct) 
Numeric - 3 digits (999) 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The police precinct in which the tax lot is located. 
10 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
This field contains a three-digit police precinct number which is preceded with 
leading zeros if the precinct number has less than three digits. 
POLICE PRECINCT contains the value returned by Geosupport for one of the 
addresses assigned to the lot. If Geosupport does not return a value, POLICE 
PRECINCT is calculated spatially using the tax lot’s XY COORDINATES and 
DCP’s Administrative District Base Map files. 
Field Name: 
Format:  
Data Source:  
Description:  
HEALTH CENTER DISTRICT (HealthCenterDist) 
Numeric - 2 digits (99) 
Department of City Planning – Geosupport System  
Department of City Planning – Administrative District Base Map files 
The health center district in which the tax lot is located. Thirty health center districts 
were created by the City in 1930 to conduct neighborhood focused health 
interventions. 
This field contains a two-digit health district number. 
HEALTH CENTER DISTRICT contains the value returned by Geosupport for one of 
the addresses assigned to the lot. If Geosupport does not return a value, HEALTH 
CENTER DISTRICT is calculated spatially using the tax lot’s XY COORDINATES 
and DCP’s Administrative District Base Map files. 
Field Name: 
Format:  
Data Source:  
Description:  
HEALTH AREA (HealthArea) 
Numeric - 4 digits (9999) 
Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
The health area in which the tax lot is located.  
Health areas were originally created in the 1920s for the purpose of reporting and  
statistical analysis of public health data. They were based on census tracts and created 
to be areas of equal population. Health areas are contained within health center 
districts. 
This field contains a four-digit health area number, which is preceded with leading 
zeros when the health area is less than four digits. There is an implied decimal point 
after the first two digits. 
HEALTH AREA contains the value returned by Geosupport for one of the addresses 
assigned to the lot. If Geosupport does not return a value, HEALTH AREA is 
11 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
12 
 
calculated spatially using the tax lot’s XY COORDINATES and DCP’s 
Administrative District Base Map files. 
 
 
 
Field Name: SANITATION DISTRICT BORO (SanitBoro) 
  
Format:  Numeric - 1 digit 
 
Data Source:  Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
 
Description:  The borough of the sanitation district that services the tax lot. 
 
Value  Borough name 
1 Manhattan 
2 Bronx 
3 Brooklyn 
4   Queens 
5  Staten Island 
 
SANITATION DISTRICT BORO contains the value returned by Geosupport for one 
of the addresses assigned to the lot. If Geosupport does not return a value, 
SANITATION DISTRICT BORO is calculated spatially using the tax lot’s XY 
COORDINATES and DCP’s Administrative District Base Map files. 
 
 
 
Field Name: SANITATION DISTRICT NUMBER (SanitDist) 
  
Format:  Numeric – 2 digits  
 
Data Source:  Department of City Planning – Geosupport System 
Department of City Planning – Administrative District Base Map files 
 
Description:  The sanitation district that services the tax lot. 
 
SANITATION DISTRICT NUMBER contains the value returned by Geosupport for 
one of the addresses assigned to the lot. If Geosupport does not return a value, 
SANITATION DISTRICT NUMBER is calculated spatially using the tax lot’s XY 
COORDINATES and DCP’s Administrative District Base Map files. 
 
 
 
Field Name: SANITATION SUBSECTION (SanitSub) 
  
Format:  Alphanumeric – 2 characters   
 
Data Source:  Department of City Planning – Geosupport System 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Department of City Planning – Administrative District Base Map files 
Description:  
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format:  
Data Source:  
Description: 
The subsection of the sanitation district that services the tax lot. 
SANITATION SUBSECTION contains the value returned by Geosupport for one of 
the addresses assigned to the lot. If Geosupport does not return a value, 
SANITATION SUBSECTION is calculated spatially using the tax lot’s XY 
COORDINATES and DCP’s Administrative District Base Map files. 
ADDRESS  (Address) 
Alphanumeric - 28 characters 
Department of Finance - Property Tax System (PTS) 
An address for the tax lot. 
Tax lots may be assigned a single house number on a street, a range of house numbers 
on a street, or addresses on multiple streets. ADDRESS contains the address in PTS, 
using the low number when there is a range of house numbers. Some tax lots, such as 
vacant lots or parks, have only a street name and no house number.  
A complete list of the addresses assigned to a tax lot is available through Geosupport 
or by downloading the Property Address Directory (PAD) from the BYTES of the 
BIG APPLETM.  
Most house numbers in Queens contain a hyphen. 
ZONING DISTRICT 1  (ZoneDist1) 
Alphanumeric - 9 characters  
Department of City Planning NYC GIS Zoning Features 
The zoning district classification of the tax lot. Under the Zoning Resolution, the map 
of New York City is generally apportioned into three basic zoning district categories: 
Residence (R), Commercial (C) and Manufacturing (M), which are further divided 
into a range of individual zoning districts, denoted by different number and letter 
combinations. In general, the higher the number immediately following the first letter 
(R, C or M), the higher the density or intensity of land use permitted.  
If the tax lot is divided by a zoning boundary line, ZONING DISTRICT 1 represents 
the zoning district classification occupying the greatest percentage of the tax lot’s 
area.  
For example: Tax lot 98 is divided by a zoning boundary line into part A and part B.  
Part A, the largest portion of the lot, is in a commercial zoning district, while part B is 
13 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
14 
 
in a residential zoning district.  ZONING DISTRICT 1 will contain the commercial 
zoning district associated with part A. 
 
Tax lots that intersect with areas designated in NYC Zoning Districts as PARK, 
BALL FIELD, PLAYGROUND, and PUBLIC SPACE are assigned a single value of 
PARK in PLUTO. The NYC Zoning Districts do not constitute a definitive list of 
parks in the city. Lots designated as PARK should not be used to calculate the amount 
of open space in an area. 
 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
 
 
 
 
 
 
 
 
 
 
 
 
 
Field Name: ZONING DISTRICT 2  (ZoneDist2) 
 
Format: Alphanumeric - 9 characters  
 
Data Source: Department of City Planning NYC GIS Zoning Features 
 
Description: If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 2 represents 
the zoning classification occupying the second greatest percentage of the tax lot's 
area. Only zoning districts that cover at least 10% of a tax lot’s area are included. 
 
If the tax lot is not divided by a zoning boundary line, the field is blank. 
 
For example:  Tax lot 98 is divided by a zoning boundary line into part A and part B.  
Part A, the larger portion of the lot, is in a commercial zoning district, while part B is 
in a residential zoning district.  ZONING DISTRICT 2 will contain the residential 
zoning district associated with part B. 
 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
 
 
 
Field Name: ZONING DISTRICT 3  (ZoneDist3) 
 
Format: Alphanumeric - 9 characters  
 
Data Source: Department of City Planning NYC GIS Zoning Features 
 
Abbreviation Description 
R1-1 - R10H Residential Districts 
C1-6 - C8-4 Commercial Districts 
M1-1 – M3-2 Manufacturing Districts 
M1-1/R5 – M1-9/R12 Mixed Manufacturing & Residential Districts 
BPC Battery Park City 
PARK 
 
Areas designated as PARK, BALL FIELD, 
PLAYGROUND and PUBLIC SPACE in NYC 
Zoning Districts 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 3 represents 
the zoning classification occupying the third greatest percentage of the tax lot's area. 
Only zoning districts that cover at least 10% of a tax lot’s area are included. 
If the tax lot is not split between three zoning districts, the field is blank. 
For example: Tax lot 98 is divided by zoning boundary lines into three sections - part 
A, part B and part C. Part A represents the largest portion of the lot, part B is the 
second largest portion of the lot, and part C covers the smallest portion of the tax lot. 
ZONING DISTRICT 3 will contain the zoning associated with part C. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
ZONING DISTRICT 4  (ZoneDist4) 
Alphanumeric - 9 characters  
Department of City Planning NYC GIS Zoning Features 
If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 4 represents 
the zoning classification occupying the fourth greatest percentage of the tax lot's area. 
Only zoning districts that cover at least 10% of a tax lot’s area are included. 
If the tax lot is not split between four zoning districts, the field is blank. 
For example: Tax lot 98 is divided by zoning boundary lines into four sections - part 
A, part B, part C and part D. Part A represents the largest portion of the lot, part B is 
the second largest portion of the lot, part C represents the third largest portion of the 
lot, and part D covers the smallest portion of the tax lot. ZONING DISTRICT 4 will 
contain the zoning associated with part D. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
COMMERCIAL OVERLAY 1  (Overlay1) 
Alphanumeric - 4 characters 
Department of City Planning NYC GIS Zoning Features 
The commercial overlay assigned to the tax lot. A commercial overlay is a C1 or C2 
zoning district mapped within residential zoning districts to serve local retail needs 
(grocery stores, dry cleaners, restaurants, for example).  
If more than one commercial overlay exists on the tax lot, COMMERCIAL 
OVERLAY 1 represents the commercial overlay occupying the greatest percentage of 
the lot area. The commercial overlay district must either cover at least 10% of a tax 
15 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
lot’s area or at least 50% of the commercial overlay district must be contained within 
the tax lot. 
If the tax lot is does not contain a commercial overlay, the field is blank. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
COMMERCIAL OVERLAY 2  (Overlay2) 
Alphanumeric - 4 characters 
Department of City Planning NYC GIS Zoning Features 
A commercial overlay assigned to the tax lot.  
If the tax lot has more than one commercial overlays, COMMERCIAL OVERLAY 2 
represents the commercial overlay occupying the second largest percentage of the tax 
lot's area. The commercial overlay district must either cover at least 10% of a tax lot’s 
area or at least 50% of the commercial overlay district must be contained within the 
tax lot. 
If the tax lot is not divided by two commercial overlays the field is blank. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
SPECIAL PURPOSE DISTRICT 1  (SPDist1) 
Alphanumeric - 12 characters 
Department of City Planning NYC GIS Zoning Features 
The special purpose district assigned to the tax lot. The regulations for special purpose 
districts are designed to supplement and modify the underlying zoning in order to 
respond to distinctive neighborhoods with particular issues and goals. Only special 
purpose districts that cover at least 10% of a tax lot’s area are included. 
If the tax lot is not in a special purpose district, the field is blank. 
If more than one special purpose district exists on the tax lot, SPECIAL PURPOSE 
DISTRICT 1 represents the special purpose district occupying the greatest percentage 
of the lot area. If the greatest percentage is occupied by two special purpose districts 
that overlap each other and cover the same percentage of the lot, SPECIAL 
PURPOSE DISTRICT 1 contains both special purpose districts. separated by “/”. 
• See Appendix A for valid values. 
16 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
SPECIAL PURPOSE DISTRICT 2  (SPDist2) 
Alphanumeric - 12 characters 
Department of City Planning NYC GIS Zoning Features 
The special purpose district assigned to the tax lot. The regulations for special purpose 
districts are designed to supplement and modify the underlying zoning in order to 
respond to distinctive neighborhoods with particular issues and goals. Only special 
purpose districts that cover at least 10% of a tax lot’s area are included. 
If the tax lot is not divided by at least two special purpose districts, the field is blank. 
If more than one special purpose district exists on the tax lot, SPECIAL PURPOSE 
DISTRICT 2 represents the special purpose district occupying the second greatest 
percentage of the lot area. If the second greatest percentage is occupied by two special 
purpose districts that overlap each other and cover the same percentage of the lot, 
SPECIAL PURPOSE DISTRICT 2 contains both special purpose districts. separated 
by “/”. 
See Appendix A for valid values. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
SPECIAL PURPOSE DISTRICT 3  (SPDist3) 
Alphanumeric - 12 characters 
Department of City Planning NYC GIS Zoning Features 
The special purpose district assigned to the tax lot. The regulations for special purpose 
districts are designed to supplement and modify the underlying zoning in order to 
respond to distinctive neighborhoods with particular issues and goals. Only special 
purpose districts that cover at least 10% of a tax lot’s area are included. 
If the tax lot is not divided by at least three special purpose districts, the field is blank. 
If the tax lot has more than two special purpose districts, SPECIAL PURPOSE 
DISTRICT 3 represents the special purpose district occupying the smallest percentage 
of the lot area.  
See Appendix A for valid values. 
See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. 
17 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
LIMITED HEIGHT DISTRICT  (LtdHeight) 
Alphanumeric - 5 characters 
Department of City Planning NYC GIS Zoning Features 
The limited height district assigned to the tax lot. A limited height district is 
superimposed on an area designated as an historic district by the Landmarks 
Preservation Commission. 
See Appendix B for valid values. 
SPLIT BOUNDARY INDICATOR  (SplitZone) 
Alphanumeric - 1 character 
Department of City Planning NYC GIS Zoning Features 
A code indicating whether the tax lot is split between multiple zoning features. The 
split boundary indicator is equal to “Y” if the tax lot has a value for ZONING 
DISTRICT 2, COMMERCIAL OVERLAY 2, or SPECIAL DISTRICT 
BOUNDARY 2.  
BUILDING CLASS  (BldgClass) 
Alphanumeric - 2 characters 
Department of City Planning - based on data from: 
Department of Finance - Property Tax System (PTS) 
A code describing the major use of structures on the tax lot. 
Except as described below, BUILDING CLASS is taken from PTS without 
modification. 
For condominiums, PTS contains the building class for each unit lot. When merging 
this data into a single record for the billing lot, DCP creates several mixed-use 
building classes (RC, RD, RI, RM, RX, and RZ). These are assigned as follows: 
• If all unit lots have the same building class, that building class is used for the 
billing lot. 
• PTS building class types are grouped as follows:  
o Commercial - R5, R7, R8, RA, RB, RH, and RK 
18 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
o Residential - R1, R2, R3, R4, R6, and RR 
o Mixed commercial and residential – R9 
o Industrial/warehouse - RW 
• If the unit lots are a mixture of commercial building types, BUILDING 
CLASS = RC. 
• If the unit lots are a mixture of residential building types, BUILDING 
CLASS = RD. 
• If the unit lots are a mixture of commercial and residential building types, 
BUILDING CLASS = RM. 
• If the unit lots are a mixture of commercial and industrial/warehouse building 
types, BUILDING CLASS = RI. 
• If the unit lots are a mixture of commercial, residential, and 
industrial/warehouse building types, BUILDING CLASS = RX. 
• If the unit lots are a mixture of residential and industrial/warehouse building 
types, BUILDING CLASS = RZ. 
• When unit lots with a building class of RG (Indoor Parking), RP (Outdoor 
Parking), RS (Non-Business Storage Space), or RT 
(Terraces/Gardens/Cabanas) have the same billing lot as another building 
class, their building class is ignored. For example, if the billing lot has unit 
lots with a building class of R4 (Residential Unit in Elevator Bldg) and RG 
(Indoor Parking), BUILDING CLASS = R4.  
Q0 is assigned by DCP to tax lots with a PTS building class starting with “V” that are 
identified in the NYC GIS Zoning Database as PARK, BALL FIELD, 
PLAYGROUND, or PUBLIC SPACE.  
QG is assigned by DCP to tax lots with a PTS building class starting with “V” that 
contain community gardens from the Department of Parks and Recreation’s NYC 
Greenthumb Community Gardens dataset. This is done to comply with Local Law 46 
of 2020, which requires that such lots be given a land use category of open space, 
outdoor recreation, a community garden, or other similar description. Lots with a 
BUILDING CLASS of QG are assigned to LAND USE CATEGORY “09” (Open 
Space & Outdoor Recreation). This land use assignment is solely informational and 
does not confer or change a legal status for such a tax lot. 
PTS contains two building classes for some tax lots, with one of the building classes 
being Z7 (Easement). BUILDING CLASS is only set to Z7 when it is the only PTS 
building class for the tax lot. 
See Appendix C - Building Class Codes for valid values  
Field Name: 
Format: 
Data Source: 
LAND USE CATEGORY  (LandUse) 
Alphanumeric - 2 characters 
Department of City Planning  
19 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
20 
 
Description: A code for the tax lot's land use category. 
 
The Department of City Planning has created 11 land use categories and assigns each 
BUILDING CLASS to the most appropriate land use category.   
 
Appendix D - Land Use Categories details the relationship of building classes to land 
use categories. 
 
VALUE DESCRIPTION 
01 One & Two Family Buildings 
02 Multi-Family Walk-Up Buildings 
03 Multi-Family Elevator Buildings 
04 Mixed Residential & Commercial Buildings 
05 Commercial & Office Buildings 
06 Industrial & Manufacturing 
07 Transportation & Utility 
08 Public Facilities & Institutions 
09 Open Space & Outdoor Recreation 
10 Parking Facilities 
11 Vacant Land 
 
 
Field Name: NUMBER OF  EASEMENTS (Easements) 
 
Format: Numeric - 2 digits (99) 
 
Data Source: Department of Finance – Property Tax System (PTS) 
 
Description: The number of unique easements on the tax lot. 
 
 PTS contains a record for each easement. NUMBER OF EASEMENTS is calculated 
by counting the number of unique PTS easement records for the tax lot. 
 
If the number of easements is zero, the tax lot has no easements. 
 
 
Field Name: TYPE OF OWNERSHIP CODE  (OwnerType) 
 
Format: Alphanumeric - 1 character 
 
Data Source: Department of City Planning - City Owned and Leased Properties (COLP) 
Department of Finance - Property Tax System (PTS) 
 
Description: A code indicating type of ownership for the tax lot. 
 
Only one data source is used per tax lot. 
 
The COLP file, which contains more accurate and specific type of city ownership data 
than PTS, is used when data is available for that lot. Codes C, M, O, P are derived 
from COLP. 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
If the tax lot is not in COLP, PTS is checked to see if the lot’s EXEMPT TOTAL 
VALUE equals its ASSESSED TOTAL VALUE.  If the two values are the same, the 
lot is given a code of X.  Otherwise the tax lot is not given any TYPE OF 
OWNERSHIP CODE. 
OWNER NAME should be referenced to verify type of ownership, particularly when 
it’s important to distinguish between state, federal, and public authority ownership.  
Value 
Description 
C 
M 
O 
P 
X 
blank 
Field Name: 
City ownership 
Mixed city & private ownership 
Other – owned by either a public authority or the state or federal 
government 
Private ownership 
Fully tax-exempt property that may be owned by the city, state, or 
federal government; a public authority; or a private institution 
Unknown (usually private ownership) 
OWNER NAME  (OwnerName) 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Alphanumeric - 81 characters 
Department of Finance - Property Tax System (PTS) 
Department of City Planning – PLUTO_input_research.csv, field ownername 
The name of the owner of the tax lot. 
For publicly owned tax lots, owner names have been normalized. For example, “NYC 
PARKS”, “PARKS DEPARTMENT”, and “PARKS AND RECREATION 
(GENERAL)” have been changed to “NYC DEPARTMENT OF PARKS AND 
RECREATION”. 
If OWNER NAME is normalized, DCPEdited is set to “1”. (see CHANGED BY 
DCP). 
LOT AREA  (LotArea) 
Numeric - 9 digits (999999999) 
Department of Finance - Property Tax System (PTS) 
Department of City Planning - based on data from: 
Department of Finance – Digital Tax Map (DTM) 
Total area of the tax lot, expressed in square feet rounded to the nearest integer. 
21 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
LOT AREA contains street beds when the tax lot contains “paper streets” i.e., streets 
mapped but not built. 
If the tax lot is not an irregularly shaped lot (see IRREGULAR LOT CODE) the 
Department of Finance calculates the LOT AREA by multiplying the LOT 
FRONTAGE by the LOT DEPTH.  If the tax lot is irregularly shaped, DOF calculates 
the LOT AREA from the Digital Tax Map. 
If PTS contains a zero value for LOT AREA, this field is changed to show the area of 
the tax lot’s geometric shape in the Digital Tax Map and DCPEdited is set to “1”. (see 
CHANGED BY DCP). 
Field Name: 
Format: 
Data Source: 
Description: 
TOTAL BUILDING FLOOR AREA (BldgArea) 
Numeric - 11 digits (99999999999) 
Department of City Planning - based on data from: 
Department of Finance - Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
The total gross area in square feet, except for condominium measurements which 
come from the Condo Declaration and are net square footage not gross. 
TOTAL BUILDING FLOOR AREA is populated in the following order of 
preference: 
1. Gross floor area from PTS 
2. Gross floor area from CAMA 
3. Calculated from the PTS building dimensions and number of stories for the 
primary building on the lot. TOTAL BUILDING FLOOR AREA calculated 
by this method will not include floor area for any other buildings on the lot. 
4. TOTAL BUILDING FLOOR AREA is set to zero if the building class starts 
with “V” and the number of buildings is zero. 
See TOTAL BUILDING FLOOR AREA SOURCE CODE to determine which 
method was used.  
If TOTAL BUILDING FLOOR AREA SOURCE CODE has a value of 2 (PTS) or 7 
(CAMA), the TOTAL BUILDING FLOOR AREA is based on gross building area, 
also known as total gross square feet.  For these data sources, the TOTAL BUILDING 
FLOOR AREA is for all of the structures on the tax lot, including stairwells, halls, 
elevator shafts, attics and extensions such as attached garages.  Measurements are 
based on exterior dimensions and take into account setbacks. 
If the TOTAL BUILDING FLOOR AREA SOURCE CODE field has a value of 5, 
the floor area was calculated from the DOF Property Tax System (PTS) using the 
building dimensions and number of stories for ONLY the largest structure on the tax 
lot. 
22 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
In all cases, this is a rough estimate of the gross building floor area and does not 
necessarily take into account all the criteria for calculating floor area as defined in 
section 12-10 of the Zoning Resolution. 
Roof areas used for parking/garden/playground are not included in the floor area. 
If TOTAL BUILDING FLOOR AREA SOURCE CODE is 2, TOTAL BUILDING 
FLOOR AREA contains the common area for condominiums. 
If FLOOR AREA, TOTAL BUILDING SOURCE CODE is 7, TOTAL BUILDING 
FLOOR AREA does not include below grade finished basements.  
If the basement in a one, two or three family structure is above grade and finished, its 
square footage is included in TOTAL BUILDING FLOOR AREA. 
A TOTAL BUILDING FLOOR AREA of zero can mean it is either not available or 
not applicable.  If NUMBER OF BUILDINGS is greater than zero, then a TOTAL 
BUILDING FLOOR AREA of zero means it is not available.  If NUMBER OF 
BUILDINGS is zero, then a TOTAL BUILDING FLOOR AREA of zero means it is 
not applicable. 
Field Name: 
Format: 
Data Source: 
Description: 
COMMERCIAL FLOOR AREA (ComArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
commercial use. 
Value is taken from PTS, if available. When calculated from PTS data, 
COMMERCIAL FLOOR AREA is the sum of floor areas for office, retail, garage, 
storage, factory, and other uses. If these fields are not populated in PTS, the value is 
taken from CAMA. 
Originally square footage came from sketches, but, for both new construction and 
alterations, it now comes from site visits. 
Basement square footage may be included in COMMERCIAL FLOOR AREA if the 
commercial buildings meets two of the three following criteria: 
• Finished 
• Active 
• Publicly accessible 
23 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
For condominiums, COMMERCIAL FLOOR AREA is the sum of the commercial 
floor area for condominium lots with the same billing lot. COMMERCIAL FLOOR 
AREA does not contain the condominium’s common area.  
A COMMERCIAL FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
RESIDENTIAL FLOOR AREA (ResArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
residential use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
For condominiums, RESIDENTIAL FLOOR AREA is the sum of the residential floor 
area for condominium lots with the same billing lot. RESIDENTIAL FLOOR AREA 
does not contain the condominium’s common area. 
A RESIDENTIAL FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
OFFICE FLOOR AREA (OfficeArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
24 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
office use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
An OFFICE FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
RETAIL FLOOR AREA (RetailArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
retail use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
A RETAIL FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
GARAGE FLOOR AREA (GarageArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
25 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
garage use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
A GARAGE FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
STORAGE FLOOR AREA (StrgeArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
storage or loft purposes.   
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
A STORAGE FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
FACTORY FLOOR AREA (FactryArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
26 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
factory, warehouse or loft use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
A FACTORY FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
OTHER FLOOR AREA (OtherArea) 
Numeric - 11 digits (99999999999) 
Department of Finance – Property Tax System (PTS) 
Department of Finance - Mass Appraisal System (CAMA) 
An estimate of the exterior dimensions of the portion of the structure(s) allocated for 
other than commercial, residential, office, retail, garage, storage, or factory use. 
Value is taken from PTS, if available. Otherwise it comes from CAMA. 
This information is NOT available for one, two or three family structures. 
An OTHER FLOOR AREA of zero can mean it is either not available or not 
applicable. 
An update to the floor area is triggered by the issuance of a Department of Buildings 
permit, feedback from the public, or site visits by Department of Finance assessors. 
The sum of the various floor area fields does not always equal TOTAL BUILDING 
FLOOR AREA. 
TOTAL BUILDING FLOOR AREA SOURCE CODE  (AreaSource) 
Alphanumeric - 1 character 
Department of City Planning 
27 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
Field Name: 
Format: 
Data Source: 
A code indicating the methodology used to determine the tax lot's TOTAL 
BUILDING FLOOR AREA (BldgArea) 
Only one source is used per tax lot. 
Value 
Methodology 
0 
2 
4 
5 
7 
Not Available 
Department of Finance's Property Tax System (PTS) 
BUILDING CLASS starts with 'V' and NUMBER OF BUILDINGS is 
0.  TOTAL BUILDING FLOOR AREA is 0. 
Calculated from PTS building dimensions and NUMBER OF 
FLOORS for primary building only. 
Department of Finance’s Mass Appraisal System (CAMA) 
NUMBER OF BUILDINGS (NumBldgs) 
Numeric - 5 digits (99999) 
Department of Information Technology and Telecommunications – Building 
Footprints 
Department of City Planning – Geosupport System 
Department of Finance – Property Tax System (PTS) 
Description: 
The number of buildings on the tax lot. 
The number of buildings on a lot is calculated by taking the Building Identification Number (BIN) for 
every building in DoITT’s Building Footprints dataset, running Geosupport function 
BN to get the BBL associated with that BIN, and summing the number of buildings 
per tax lot. 
Field Name: 
Format: 
Data Source: 
Description: 
NUMBER OF FLOORS (NumFloors) 
Numeric - 6 digits (999.99) 
Department of Finance – Property Tax System (PTS) 
The number of full and partial floors starting from the ground floor, for the tallest 
building on the tax lot. A partial floor is a floor that does not span the entire building 
envelope. For example, if a building is 3 stories tall and 2 floors cover the entire 
footprint of the building and one floor covers half of the footprint, the number of 
floors would be 2.5. 
Above ground basements are not included in the NUMBER OF FLOORS. 
A roof used for parking, farming, playground, etc. is not included in NUMBER OF 
FLOORS. 
If the NUMBER OF FLOORS is null and the NUMBER OF BUILDINGS is greater 
than zero, then NUMBER OF FLOORS is not available for the tax lot. 
28 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
RESIDENTIAL UNITS (UnitsRes) 
Numeric - 5 digits (99999) 
Department of Finance - Property Tax System (PTS) 
The sum of residential units in all buildings on the tax lot. 
If there are no residential units in the tax lot, this field will be zero. 
Hotels/motels, nursing homes and SROs do not have residential units, but boarding 
houses do. Basement units for building superintendents are counted as a residential 
unit. 
An update to residential units is triggered by the issuance of a Department of 
Buildings permit. 
TOTAL UNITS (UnitsTotal) 
Numeric - 5 digits (99999) 
Department of Finance - Property Tax System (PTS) 
The sum of residential and non-residential (offices, retail stores, etc.) units for all 
buildings on the tax lot. 
The count of non-residential units is sometimes not available if the building contains 
residential units. 
Non-residential units are units with a separate use.  If a building has 25 different 
offices it would be counted as 1 unit because they have the same use. 
Updates to residential and non-residential units are triggered by the issuance of a 
Department of Buildings permit.  
LOT FRONTAGE  (LotFront) 
Numeric - 7 digits (9999.99) 
Department of Finance - Property Tax System (PTS) 
The tax lot's frontage measured in feet. 
29 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
NOTE:        
Field Name: 
It appears that if a lot fronts on more than one street, the PTS building 
address often determines which side of the lot used for calculating lot 
frontage. 
LOT DEPTH  (LotDepth) 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Numeric - 7 digits (9999.99) 
Department of Finance - Property Tax System (PTS) 
The tax lot's depth measured in feet. 
BUILDING FRONTAGE  (BldgFront) 
Numeric - 7 digits (9999.99) 
Department of Finance - Property Tax System (PTS) 
The building’s frontage along the street measured in feet. 
BUILDING DEPTH  (BldgDepth) 
Numeric - 7 digits (9999.99) 
Department of Finance - Property Tax System (PTS) 
The building’s depth, which is the effective perpendicular distance, measured in feet. 
EXTENSION CODE  (Ext) 
Alphanumeric – 2 Characters 
Department of Finance - Property Tax System (PTS) 
A code identifying whether there is an extension on the lot or a garage other than the 
primary structure.   
30 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
31 
 
Value Description 
E Extension 
G Garage 
EG 
N 
Blank 
Extension and garage 
None 
Unknown 
 
 
Field Name: PROXIMITY CODE  (ProxCode) 
 
Format: Alphanumeric - 1 character 
 
Data Source: Department of Finance - Mass Appraisal System (CAMA) 
 
Description: A code describing the physical relationship of the building to neighboring buildings. 
If there are multiple buildings on the lot, CAMA data for building number 1 is used. 
 
Value Description 
0 Not available 
1 Detached 
2 Semi-attached 
3 Attached 
 
 
 
Field Name: IRREGULAR LOT CODE  (IrrLotCode) 
 
Format: Alphanumeric - 1 character 
 
Data Source: Department of Finance - Property Tax System (PTS) 
 
Description: A code indicating whether the tax lot is irregularly shaped. 
 
Value Description 
Y Yes, an irregularly shaped lot 
N No, not an irregularly shaped lot 
blank Unknown 
 
 
Field Name: LOT TYPE   (LotType) 
 
Format: Alphanumeric - 1 character 
 
Data Source: Department of Finance - Mass Appraisal System (CAMA) 
 
Description: A code indicating the location of the tax lot in relationship to another tax lot and/or 
the water. 
 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
CAMA may contain multiple lot types for a tax lot. For instance, a lot may be both a corner lot and 
waterfront lot. DCP assigns LOT TYPE by taking the lowest CAMA lot type for the 
tax lot, with the exception of LOT TYPE 5, which is only assigned if the lot has no 
other lot types in CAMA. 
Value 
Description 
0 
1 
2 
3 
4 
5 
6 
7 
8 
9 
Field Name: 
Unknown 
Block assemblage – a tax lot that encompasses an entire block 
Waterfront – a tax lot bordering on a body of water.  Waterfront 
lots may contain a small amount of submerged land. 
Corner – a tax lot bordering on two intersecting streets 
Through – a tax lot connecting two streets, with frontage on both 
streets. Note that a lot with two frontages is not necessarily a 
through lot. For example, an L-shaped lot with two frontages is 
considered an inside lot (5). 
Inside – a tax lot with frontage on only one street. This value comes 
from CAMA, but is only assigned in PLUTO if CAMA has no other 
lot types for the tax lot. 
Interior lot – a tax lot that has no street frontage 
Island lot – a tax lot that is entirely surrounded by water 
Alley lot – a tax lot that is too narrow to accommodate a building. 
The lot is usually 12 feet or less in width. 
Submerged land lot – a tax lot that is totally or almost completely 
submerged 
BASEMENT TYPE/GRADE  (BsmtCode) 
Format: 
Data Source: 
Description: 
Alphanumeric - 1 character 
Department of City Planning - based on data from: 
Department of Finance - Mass Appraisal System (CAMA) 
A code describing the building’s basement.  
Value 
Description 
0 
1 
None/No Basement 
Above grade full basement – the basement is 75% or more of the 
area of the first floor and the basement walls are at least 4 feet high on 
at least two sides 
32 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Value 
Description 
2 
3 
4 
5 
Below grade full basement – the basement is 75% or more of the 
area of the first floor and the basement walls are fully submerged or 
are less than 4 feet on at least three sides 
Above grade partial basement – the basement is between 25% and 
75% of the area of the first floor and the basement walls are at least 4 
feet high on at least two sides 
Below grade partial basement – the basement is between 25% and 
75% of the area of the first floor and the basement walls are fully 
submerged or are less than 4 feet on at least three sides 
Unknown 
This information is available for one, two or three family structures. 
This information may also be available for commercial buildings if two of the 
following three criteria are met: 
• Finished 
• Active 
• Publicly accessible 
A value may exist for other types of property, but the data is not verified by DOF. 
Basements in brownstones, high ranches, split-levels and attached row houses are 
considered above grade. 
A fully exposed basement garage door does not, in itself, satisfy the criteria for above 
grade. 
A cellar is below a basement and not habitable. 
Field Name: 
Format: 
Data Source: 
Description: 
ASSESSED LAND VALUE (AssessLand) 
Numeric - 11 digits (99999999999) 
Department of Finance - Property Tax System (PTS) 
The assessed land value for the tax lot. 
The Department of Finance calculates the assessed value by multiplying the tax lot’s 
estimated full market land value, determined as if vacant and unimproved, by a 
uniform percentage for the property’s tax class.  
Assessed and exempt values are updated twice a year. Tentative values are released in 
mid-January and final values are released around May 25. If the date on source file 
(PTS), as reported in the Readme file, is between January 15 and May 25, 
33 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
ASSESSED LAND VALUE is from the tentative roll for the tax year starting in July. 
Otherwise, ASSESSED LAND VALUE is from the final roll. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
ASSESSED TOTAL VALUE (AssessTot) 
Numeric - 11 digits (99999999999) 
Department of Finance - Property Tax System (PTS) 
The assessed total value for the tax lot. 
The Department of Finance (DOF) calculates the assessed value by multiplying the 
tax lot’s estimated full market value by a uniform percentage for the property’s tax 
class. 
DOF values properties based on current and constructive use, rather than legal use. The 
predominant active use, which determines the classification of a property, is determined 
by square footage. If the second story of a three-story building is mixed-use, an interior 
inspection may be necessary to establish the commercial percentage of that story before 
reclassification. In other cases, a two-story building with retail on the first floor may 
have a sign identifying a second story accounting office.  If, for example, the second 
story is a primary residence and there is a difference in square footage from the first to 
second floor, the mere presence of a business sign does not confirm a predominant 
commercial use. 
Additional research is required to ensure proper classification.  This can include an 
internal inspection, speaking to someone at the location or a neighbor, and researching 
various records (such as filed Real Property Income and Expenses statements) from 
DOF or other city agencies. 
NYC Property Tax Classes are determined by NYS and described under Real 
Property Tax Law (RPTL) Article §18-02 which mentions primary use for real 
property classification. 
Property value is assessed as of January 5th.  If a new building is not completed by 
April 14th, the assessed building value is 0 and the Building Class reverts to Vacant. 
Assessed and exempt values are updated twice a year. Tentative values are released in 
mid-January and final values are released around May 25. If the date on source file 
(PTS), as reported in the Readme file, is between January 15 and May 25, 
ASSESSED TOTAL VALUE is from the tentative roll for the tax year starting in 
July. Otherwise, ASSESSED TOTAL VALUE is from the final roll
EXEMPT TOTAL VALUE (ExemptTot) 
Numeric - 11 digits (99999999999) 
Department of Finance - Property Tax System (PTS) 
34 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Description: 
The exempt total value, which is determined differently for each exemption program, 
is the dollar amount related to that portion of the tax lot that has received an 
exemption. 
Assessed and exempt values are updated twice a year. Tentative values are released in mid-January and 
final values are released around May 25. If the date on source file (PTS), as reported 
in the Readme file, is between January 15 and May 25, EXEMPT TOTAL VALUE is 
from the tentative roll for the tax year starting in July. Otherwise, EXEMPT TOTAL 
VALUE is from the final roll. 
Note that New York State typically releases STAR exempt values right after the tentative roll is released. 
EXEMPT TOTAL VALUE will change to reflect these values after they are received. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
YEAR BUILT  (YearBuilt) 
Numeric - 4 digits (9999) 
Department of Finance - Property Tax System (PTS) 
The year construction of the building was completed. 
In general, YEAR BUILT is accurate for the decade, but not necessarily for the 
specific year. Between 1910 and 1985, the majority of YEAR BUILT values are in 
years ending in 5 or 0. Many structures built between 1800s and early 1900s have a 
YEAR BUILT between 1899 and 1901.  
For ~26,000 buildings in historic districts, YEAR BUILT has been changed to the 
date_high value from Landmarks Preservation Commission’s Individual Landmark 
and Historic District Building Database. Any tax lot updated with LPC data has a 
value of 1 in field CHANGED BY DCP. The original YEAR BUILT value can be 
found in PLUTOChangeFileYYv#.#.csv, where YYv#.# is the version number. 
If Year Built is null or 0, then the value is unknown. 
YEAR ALTERED 1  (YearAlter1) 
Numeric - 4 digits (9999) 
Department of Finance - Property Tax System (PTS) 
If a building has only been altered once, YEAR ALTERED 1 is the date that 
alteration began. 
If a building has been altered more than once, YEAR ALTERED 1 is the year of the second most recent 
alteration. 
35 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
The Department of Finance defines alterations as modifications to the structure that, 
according to the assessor, change the value of the real property. 
The date comes from Department of Buildings permits and may either be the actual 
date or an estimate. 
Field Name: 
Format: 
Data Source: 
Description: 
YEAR ALTERED 2  (YearAlter2) 
Numeric - 4 digits (9999) 
Department of Finance - Property Tax System (PTS) 
If a building has only been altered once, this field is blank. 
If a building has been altered more than once, YEAR ALTERED 2 is the year that the most recent 
alteration began. 
The Department of Finance defines alterations as modifications to the structure that, 
according to the assessor, change the value of the real property. 
The date comes from Department of Buildings permits and may either be the actual 
date or an estimate. 
Field Name: 
Format: 
Data Source:         
Description: 
Field Name: 
Format:  
Data Source:          
Description: 
Field Name: 
HISTORIC DISTRICT NAME  (HistDist) 
Alphanumeric - 40 characters 
Landmarks Preservation Commission Individual Landmark and Historic District 
Building Database 
The name of the Historic District that the tax lot is within. Historic Districts are 
designated by the New York City Landmarks Preservation Commission.  
LANDMARK STATUS  (Landmark) 
Alphanumeric - 35 characters 
Landmarks Preservation Commission Individual Landmarks dataset 
This value indicates whether the lot contains an individual landmark building, an 
interior landmark building, or both.  
BUILT FLOOR AREA RATIO (BuiltFAR) 
36 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Numeric - 7 digits (9999.99) 
Department of City Planning – based on data from: 
Department of Finance - Property Tax System (PTS) 
The BUILT FLOOR AREA RATIO is the total building floor area divided by the area 
of the tax lot. 
This is an estimate by City Planning based on rough building area and lot area 
measurements provided by the Department of Finance.  BUILT FLOOR AREA 
RATIO is calculated using the TOTAL BUILDING FLOOR AREA and the LOT 
AREA. 
MAXIMUM ALLOWABLE RESIDENTIAL FAR  (ResidFAR) 
Numeric - 5 digits (99.99) 
Department of City Planning Zoning Division   
The maximum allowable residential floor area ratio, based on the zoning district 
classification occupying the greatest percentage of the tax lot’s area as reported in 
ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does 
not allow residential uses, MAXIMUM ALLOWABLE RESIDENTIAL FAR is 
based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order. 
The maximum allowable residential floor area ratios are exclusive of bonuses for 
plazas, plaza-connected open areas, arcades, or other amenities.  
For R2X, R3, R4, and C3 zoning districts, ResidFAR does not include the attic 
allowance, under which the FAR may be increased by up to 20% for the inclusion of 
space beneath a pitched roof. 
For properties zoned R6, R7, R7-1, R8 or R9, ResidFAR reflects the maximum 
achievable floor area under ideal conditions. 
The maximum allowable floor area does not reflect Voluntary Inclusionary Housing 
or Mandatory Inclusionary Housing Program floor area. See Appendix F and Section 
23-154, paragraphs (b) and (d) of the Zoning Resolution. 
For properties in special mixed use districts, PLUTO uses the wide street maximum 
allowable floor area ratio.  Since the maximum allowable floor area ratio in mixed use 
special districts is actually determined by whether the property is located on a wide 
street or a narrow street, users should consult Section 23-153 of the Zoning 
Resolution.  
MAXIMUM ALLOWABLE COMMERCIAL FAR  (CommFAR) 
Numeric - 5 digits (99.99) 
37 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Department of City Planning Zoning Division   
The maximum allowable commercial floor area ratio, based on the zoning district 
classification occupying the greatest percentage of the tax lot’s area as reported in 
ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does 
not allow commercial uses, MAXIMUM ALLOWABLE COMMERCIAL FAR is 
based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order. 
The maximum allowable commercial floor area ratios are exclusive of bonuses for 
plazas, plaza-connected open areas, arcades, or other amenities.  
Users should consult Section 43-12 of the Zoning Resolution for more information.  
MAXIMUM ALLOWABLE COMMUNITY FACILITY FAR  (FacilFAR) 
Numeric - 5 digits (99.99) 
Department of City Planning Zoning Division   
The maximum allowable community facility floor area ratio, based on the zoning 
district classification occupying the greatest percentage of the tax lot’s area as 
reported in ZoneDist1. If the lot is assigned to more than one zoning district and 
ZoneDist1 does not allow community facility uses, MAXIMUM ALLOWABLE 
COMMUNITY FACILITY FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in 
that order. 
The maximum allowable community facility floor area ratios are exclusive of bonuses 
for plazas, plaza-connected open areas, arcades, or other amenities.  
Users should consult Section 24-11 of the Zoning Resolution for more information. 
BORO CODE  (BoroCode) 
Numeric - 1 digit (9) 
Department of Finance - Property Tax System (PTS) 
The borough in which the tax lot is located. 
Value 
Description 
1 
2 
3 
4 
5 
Manhattan 
Bronx 
Brooklyn 
Queens 
Staten Island 
38 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Two portions of the city, Marble Hill and Rikers Island, are legally located in one 
borough but are serviced by a different borough. The BORO CODEs associated with 
these areas are the boroughs in which they are legally located. 
Marble Hill is serviced by the Bronx, but is legally located in Manhattan and has a 
BORO CODE of 1. Rikers Island is serviced by Queens, but is legally located in the 
Bronx and has a BORO CODE of 2. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
BOROUGH, TAX BLOCK & LOT (BBL) 
Numeric - 10 digits 
Department of City Planning - based on data from: 
Department of Finance - Property Tax System (PTS) 
A concatenation of the borough code, tax block and tax lot. 
This field consists of the borough code followed by the tax block followed by the tax 
lot.  The borough code is one numeric digit.  The tax block is one to five numeric 
digits, preceded with leading zeros when the block is less than five digits.  The tax lot 
is one to four digits and is preceded with leading zeros when the lot is less than four 
digits. 
For condominiums, the BBL is for the billing lot. See TAX LOT for more 
information on how condominiums are handled. 
Examples: 
Manhattan Borough Code 1, Tax Block 16, Tax Lot 100 would be stored as 
1000160100. 
Brooklyn Borough Code 3, Tax Block 15828, Tax Lot 7501 would be stored as 
3158287501. 
CONDOMINIUM NUMBER  (CondoNo) 
Numeric - 5 digits 
Department of Finance – Property Tax System (PTS) 
The condominium number assigned to the complex. 
Condominium numbers are unique within a borough (see BOROUGH). 
CENSUS TRACT 2  (Tract2010) 
Alphanumeric - 6 characters 
39 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Department of City Planning – Geosupport System 
The 2010 census tract in which the tax lot is located. 
This field contains a one to four-digit census tract number and a two-digit suffix.  
There is an implied decimal point between the census tract number and the suffix.  
The census tract number is preceded with leading zeros when the tract is less than 
four digits.  If the tract has no suffix, CENSUS TRACT 2 contains 4 characters.  
2010 census tracts are geographic areas defined by the U.S. Census Bureau for the 
2010 Census. 
Examples: 
Census Tract 203.01 would be stored as 020301 
Census Tract 23 would be stored as 0023 
X COORDINATE  (XCoord) 
Numeric - 7 digits (9999999) 
Department of City Planning – Geosupport System  
Department of Finance – Digital Tax Map: Calculated from centroid of tax lot 
The X coordinate of the XY coordinate pair which depicts the approximate location of 
the lot. 
If the X coordinate is not available from Geosupport, it is calculated from the centroid 
of the tax lot, with the constraint that the resulting point must be within the lot 
boundaries. 
The XY coordinates are expressed in the New York-Long Island State Plane 
coordinate system. 
Y COORDINATE  (YCoord) 
Numeric - 7 digits (9999999) 
Department of City Planning - Geosupport System 
Department of Finance – Digital Tax Map: Calculated from centroid of tax lot 
The Y coordinate of the XY coordinate pair which depicts the approximate location of 
the lot. 
If the Y coordinate is not available from Geosupport, it is calculated from the centroid 
of the tax lot, with the constraint that the resulting point must be within the lot 
boundaries  
40 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
The XY coordinates are expressed in the New York-Long Island State Plane 
coordinate system. 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
Field Name: 
Format: 
Data Source: 
Description: 
ZONING MAP #  (ZoneMap) 
Alphanumeric - 3 characters 
Department of City Planning Georeferenced NYC Zoning Maps 
The Department of City Planning Zoning Map Number associated with the tax lot’s X 
and Y Coordinates. If the tax lot is on the border of two or more zoning maps, 
ZONING MAP # is the zoning map covering the greatest area. 
ZONING MAP CODE  (ZMCode) 
Alphanumeric – 1 character 
Department of City Planning Georeferenced NYC Zoning Maps 
A code (Y) identifies a tax lot on the border of two or more zoning maps. 
SANBORN MAP #  (Sanborn) 
Alphanumeric - 8 characters 
Department of City Planning – Geosupport System 
The Sanborn Map Company map number associated with the tax block and lot. 
SANBORN MAP # format is Borough Code/Volume Number/Page Number,  
where Borough Code is 1 (Manhattan), 2 (Bronx), 3 (Brooklyn), 4 (Queens), or 5 
(Staten Island) 
For example:  the SANBORN MAP # associated with tax block 154, tax lot 23 in 
Manhattan is 1/01S/020. 
This field has been deprecated and will be removed at a future date. The data in the 
field cannot be considered reliable. 
TAX MAP #  (TaxMap) 
Alphanumeric - 5 characters 
Department of City Planning – Geosupport System 
The Department of Finance paper tax map volume number associated with the tax 
block and lot.   
41 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
The first character of the Tax Map # is the Borough Code – 1 (Manhattan), 2 (Bronx), 
3 (Brooklyn), 4 (Queens), or 5 (Staten Island). The second and third characters are the 
Section Number and the fourth and fifth characters are the Volume Number. 
NOTE: The Department of Finance no longer updates their paper tax maps. 
Field Name: 
Format: 
Data Source: 
Description: 
E-DESIGNATION NUMBER  (EDesigNum) 
Alphanumeric - 5 characters 
Department of City Planning – E-Designation File 
The (E) designation number assigned to the tax lot. An (E) designation provides 
notice of the presence of an environmental requirement pertaining to potential 
hazardous materials contamination, high ambient noise levels or air emission 
concerns on a particular tax lot. 
Note that a tax lot may have more than one (E) designation. See the source file for all designations on the 
lot.  
Field Name: 
Format: 
Data Source: 
Description: 
APPORTIONMENT BBL (APPBBL) 
Numeric – 10 digits 
Department of Finance - Property Tax System (PTS) 
The originating BBL (borough, block and lot) from the apportionment prior to the 
merge, split or property’s conversion to a condominium.   
APPORTIONMENT BBL is only available for mergers, splits, and conversions since 1984.   
Field Name: 
Format: 
Data Source: 
Description: 
APPORTIONMENT DATE (APPDate) 
Numeric – 10 characters 
Department of City Planning - based on data from: 
Department of Finance - Property Tax System (PTS) 
The date of the apportionment. 
The data is in the format MM/DD/YYYY, where MM is a two-digit month, DD is the two-digit day, and 
YYYY is the four-digit year. 
42 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
Field Name: 
Format: 
Data Source: 
PLUTO – DTM BASE MAP INDICATOR  (PLUTOMapID) 
Numeric - 1 digit 
Department of City Planning - PLUTO Data File 
Department of City Planning – MapPLUTO (water areas included) 
Department of City Planning – MapPLUTO (clipped to shoreline) 
Department of Finance - Digital Tax Map  
Department of Finance - Shoreline File 
Department of Finance - Property Tax System (PTS) 
Description: 
A code indicating whether the tax lot is in the PLUTO file, the MapPLUTO file with 
water areas included, and/or the MapPLUTO file that is clipped to the shoreline. 
Because the Digital Tax Map (DTM) and the Property Tax System (PTS) are not updated at the same 
time, they are slightly out-of-sync. There will be lots in PTS that are not in the DTM 
and vice versa. In addition, some lots are wholly underwater and are not included in 
the version of MapPLUTO that is clipped to the shoreline.  
The lot geographies in MapPLUTO (with water areas included) are created from the DTM. City Planning 
modifies the DTM for condominium lots to show the billing tax lot in MapPLUTO, 
rather than the base tax lot. If there is more than one base tax lot with the same billing 
lot, the base tax lots are merged into a single feature and assigned to the billing lot. 
See LOT for more information on condominium lots. 
MapPLUTO (clipped to shoreline) is created by clipping the full MapPLUTO using DOF’s Shoreline 
File. 
Value 
Description 
1 
2 
3 
4 
5 
Field Name: 
Lot is in PLUTO and both versions of MapPLUTO 
Lot is in PLUTO only. 
Lot is in both versions of MapPLUTO, but not in PLUTO 
Lot is in PLUTO and MapPLUTO (with water areas included), but not 
in the clipped version of MapPLUTO. Tax lot is completely under 
water. 
Lot is in MapPLUTO (with water areas included), but not in the 
clipped version of MapPLUTO or in PLUTO. Tax lot is completely 
under water. 
2007 FLOOD INSURANCE RATE MAP INDICATOR (FIRM07_Flag)) 
Format: 
Data Source: 
Alphanumeric – 1 character 
Department of City Planning based on  
43 
PLUTO DATA DICTIONARY 
January 2026 (25v4) 
FEMA’s 2007 Flood Insurance Rate Map 
Description: 
A value of 1 means that some portion of the tax lot falls within the 1% annual chance 
floodplain as determined by FEMA’s 2007 Flood Insurance Rate Map. 
Note that buildings on the tax lot may or may not be in the portion of the tax lot that is within the 1% 
annual chance floodplain. 
Field Name: 
Format: 
Data Source: 
2015 PRELIMINARY FLOOD INSURANCE RATE MAP INDICATOR
(PFIRM15_Flag) 
Alphanumeric – 1 character 
Department of City Planning based on 
FEMA’s 2015 Preliminary Flood Insurance Rate Map 
Description: 
A value of 1 means that some portion of the tax lot falls within the 1% annual chance 
floodplain as determined by FEMA’s 2015 Preliminary Flood Insurance Rate Map. 
Note that buildings on the tax lot may or may not be in the portion of the tax lot that is within the 1% 
annual chance floodplain. 
Field Name: 
Format: 
Data Source: 
Description: 
VERSION NUMBER (Version) 
Alphanumeric – 6 characters 
Department of City Planning 
The version number for this release of PLUTO. 
The Version Number is in the format YYv#.# where: 
YY is the last two digits of the year; 
v stands for version; 
# is the release number for that year; and 
.# indicates an amendment to the original release, if applicable. 
Field Name: 
Format: 
Data Source: 
Description: 
CHANGED BY DCP (DCPEdited) 
Alphanumeric – 3 characters 
Department of City Planning 
Flag indicating that City Planning has applied a correction to the record. 
Flag set to “1” if City Planning has made a change to any field values for this tax lot. To see which 
field(s) were changed, refer to the PLUTOChangeFileYYv#.#.csv, where YYv#.# is 
44 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
45 
 
the version number. See the PLUTO change file readme document for more 
information. 
 
 
 
Field Name: LATITUDE (Latitude) 
 
Format: Numeric 
 
Data Source: Department of City Planning 
 
Description: The WGS 84 latitude of the latitude/longitude coordinate pair for the approximate 
location of the tax lot. 
 
 
 
Field Name: LONGITUDE (Longitude) 
 
Format: Numeric 
 
Data Source: Department of City Planning 
 
Description: The WGS 84 longitude of the latitude/longitude coordinate pair for the approximate 
location of the tax lot  
 
 
 
Field Name: NOTES (Notes) 
 
Format: Alphanumeric – 20 characters 
 
Data Source: Department of City Planning 
 
Description: A text field containing notes of importance to one or more lots. 
 
Value Description 
1 All zoning regulations pertaining to the Special Inwood District 
Rezoning, which amended the Zoning Resolution (N 180205A ZRM) 
and Zoning Map (C 180204A ZMM), and which have been in effect 
since 8/8/18, are no longer in effect as of 12/19/19 per court order. 
For the applicable zoning designations currently in effect, please see 
zoning maps 1b, 1d, 3a, and 3c. 
 
In July 2020, the Appellate Division First Department ruled that the 
Special Inwood District Rezoning could proceed. The value of 1 has 
been removed from all lots. 
  
  
  
  
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
46  
APPENDIX A:  SPECIAL PURPOSE DISTRICTS 
 
Abbreviation Description 
125th Special 125th Street District 
AAM 
  
Special Atlantic Avenue Mixed Use District 
  
BNY Special Brooklyn Navy Yard District 
BPC Special Battery Park City District 
BR Special Bay Ridge District 
BSC Special Bay Street Corridor District 
C Special Grand Concourse Preservation District 
CD Special City Island District 
CI Special Coney Island District 
CL Special Clinton District 
CO Special Coney Island Mixed Use District 
CP Special College Point District 
CR - n 
Special Coastal Risk District, where n is the number of the 
district 
DB Special Downtown Brooklyn District 
DFR Special Downtown Far Rockaway District 
DJ Special Downtown Jamaica District 
EC-n 
Special Enhanced Commercial District, where n is the 
number of the district 
EHC East Harlem Corridors 
ETC Special Eastchester – East Tremont Corridor District 
FH Special Forest Hills District 
FW Special Flushing Waterfront District 
G Special Gowanus Mixed Use District 
GI Special Governors Island District 
HP Special Hunts Point District 
HRP Special Hudson River Park District 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
47  
Abbreviation Description 
HRW Special Harlem River Waterfront District 
HS Special Hillsides Preservation District 
HSQ Special Hudson Square District 
HY Special Hudson Yards District 
IN Special Inwood District 
J Jerome Corridor District 
L Special Lincoln Square District 
LC Special Limited Commercial District 
LI Special Little Italy District 
LIC Special Long Island City Mixed Use District 
LM Special Lower Manhattan District 
MiD Special Midtown District 
MMU Special Manhattanville Mixed Use District 
MP Special Madison Avenue Preservation District 
MSX Special Midtown South Mixed-Use District 
MX-n 
Special Mixed-Use District, where n is the number of the 
district 
NA-n 
Special Natural Area District, where n is the number of the 
district 
NA-4 Special Fort Totten Natural Area District-4 
OP Special Ocean Parkway District 
PC Special Planned Community Preservation District 
PI Special Park Improvement District 
SB Special Sheepshead Bay District 
SG Special St. George District 
SHP Special Southern Hunters Point District 
SNX Special SoHo-NoHo Mixed Use District 
SRD Special South Richmond Development District 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
48  
Abbreviation Description 
SRI Special Southern Roosevelt Island District 
SV-1 Special Scenic View District 
SW Special Stapleton Waterfront District 
TA Special Transit Land Use District 
TMU Special Tribeca Mixed Use District 
U Special United Nations Development District 
US Special Union Square District 
WCh Special West Chelsea District 
WP Special Willets Point District 
 
 
 
 
 
APPENDIX B:  LIMITED HEIGHT DISTRICTS 
 
Abbreviation Description 
LH-1 Limited Height District No. 1 
(Gramercy Park/Brooklyn Heights/Cobble Hill) 
LH-1A Limited Height District No. 1A (Upper East Side) 
LH-2 Limited Height District No. 2* 
LH-3 Limited Height District No. 3* 
 
*There are currently no districts with these designations 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
 
1 Building Classes were developed and are assigned by the Department of Finance with the exception of Q0 
and the mixed-use condominium building classes that were developed by the Department of City Planning 
(DCP).  See the definition of BUILDING CLASS for more information. 
49 
 
APPENDIX C:  BUILDING CLASS CODES 
 
 
 
A. ONE FAMILY DWELLINGS 
0. Cape Cod 
1. Two Stories Detached (Small or Moderate 
Size, With or Without Attic) 
2. One Story (Permanent Living Quarters) 
3. Large Suburban Residence 
4. City Residence 
5. Attached or Semi-Detached 
6. Summer Cottages 
7. Mansion Type or Town House 
8. Bungalow Colony/Land Coop Owned 
9. Miscellaneous  
 
B. TWO FAMILY DWELLINGS 
1. Brick 
2. Frame 
3. Converted from One Family 
9. Miscellaneous  
 
C. WALK UP APARTMENTS 
0. Three Families 
1. Over Six Families Without Stores 
2. Five to Six Families 
3. Four Families 
4. Old Law Tenements 
5. Converted Dwelling or Rooming House 
6. Cooperative  
7. Over Six Families with Stores 
8. Co-Op Conversion from Loft/Warehouse 
9. Garden Apartments 
M. Mobile Homes/Trailer Parks 
 
D. ELEVATOR APARTMENTS 
0. Co-op Conversion from Loft/Warehouse 
1. Semi-fireproof (Without Stores) 
2. Artists in Residence 
3. Fireproof (Without Stores) 
4. Cooperatives (Other Than Condominiums) 
5. Converted 
6. Fireproof with Stores 
7. Semi-Fireproof with Stores 
8. Luxury Type 
9. Miscellaneous 
E. WAREHOUSES 
1. Fireproof  
2. Contractor’s Warehouse 
3. Semi-Fireproof 
4. Frame, Metal 
7. Warehouse, Self Storage 
9. Miscellaneous 
 
F. FACTORY AND INDUSTRIAL 
BUILDINGS 
1. Heavy Manufacturing - Fireproof 
2. Special Construction - Fireproof 
4. Semi-Fireproof 
5. Light Manufacturing 
8. Tank Farms 
9. Miscellaneous 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
50  
G. GARAGES AND GASOLINE STATIONS 
0. Residential Tax Class 1 Garage 
1. All Parking Garages 
2. Auto Body/Collision or Auto Repair 
3. Gas Station with Retail Store 
4. Gas Station with Service/Auto Repair 
5. Gas Station only with/without Small Kiosk 
6. Licensed Parking Lot 
7. Unlicensed Parking Lot 
8. Car Sales/Rental with Showroom 
9. Miscellaneous Garage or Gas Station 
U. Car Sales/Rental without Showroom 
W. Car Wash or Lubritorium Facility 
 
H. HOTELS 
1. Luxury Type 
2. Full Service Hotel 
3. Limited Service – Many Affiliated with 
National Chain 
4. Motels 
5. Private Club, Luxury Type 
6. Apartment Hotels 
7. Apartment Hotels-Co-op Owned 
8. Dormitories 
9. Miscellaneous 
B. Boutique 10-100 Rooms, with Luxury 
Facilities, Themed, Stylish, with Full Service 
Accommodations 
H. Hostel-Bed Rental in Dorm Like Setting with 
Shared Rooms & Bathrooms 
R. SRO- 1 or 2 People Housed in Individual 
Rooms in Multiple Dwelling Affordable 
Housing 
S. Extended Stay/Suite Amenities Similar to Apt., 
Typically Charge Weekly Rates & Less 
Expensive than Full Service Hotel 
 
I. HOSPITALS AND HEALTH 
1. Hospitals, Sanitariums, Mental Institutions 
2. Infirmary 
3. Dispensary 
4. Staff Facilities 
5. Health Center, Child Center, Clinic 
6. Nursing Home 
7. Adult Care Facility 
9. Miscellaneous  
 
 
 
 
J. THEATRES 
1. Art Type (Seating Capacity under 400 Seats) 
2. Art Type (Seating Capacity Over 400 Seats) 
3. Motion Picture Theatre with Balcony 
4. Legitimate Theatres (Theatre Sole Use of 
Building) 
5. Theatre in Mixed Use Building 
6. T.V. Studios 
7. Off-Broadway Type 
8. Multiplex Picture Theatre 
9. Miscellaneous  
 
K. STORE BUILDINGS (TAXPAYERS 
INCLUDED) 
1. One Story Retail Building 
2. Multi-Story Retail Building 
3. Multi-Story Department Store 
4. Predominant Retail with Other Uses 
5. Stand Alone Food Establishment 
6. Shopping Centers with or without Parking  
7. Banking Facilities with or without Parking 
8. Big Box Retail Not Affixed & Standing on 
Own Lot with Parking 
9. Miscellaneous 
 
L. LOFT BUILDINGS 
1. Over Eight Stores (Mid-Manhattan Type) 
2. Fireproof and Storage Type (Without Stores) 
3. Semi-Fireproof 
8. With Retail Stores Other Than Type 1 
9. Miscellaneous 
 
M. CHURCHES, SYNAGOGUES, ETC. 
1. Church, Synagogue, Chapel 
2. Mission House (Non-Residential) 
3. Parsonage, Rectory 
4. Convents 
9. Miscellaneous 
 
N. ASYLUMS AND HOMES 
1. Asylums 
2. Homes for Indigent Children, Aged, Homeless 
3. Orphanages 
4. Detention House For Wayward Girls 
9. Miscellaneous 
 
 
 
 
 
 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
51  
O. OFFICE BUILDINGS 
1. Office Only – 1 Story  
2. Office Only – 2-6 Stories 
3. Office Only – 7-19 Stories 
4. Office Only or Office with Comm – 20 Stories 
or More 
5. Office with Comm – 1 to 6 Stories 
6. Office with Comm – 7 to 19 Stories 
7. Professional Buildings/Stand Alone Funeral 
Homes 
8. Office with Apartments Only (No Comm) 
9. Miscellaneous and Old Style Bank Bldgs 
 
P PLACES OF PUBLIC ASSEMBLY 
(INDOOR) AND CULTURAL 
1. Concert Halls 
2. Lodge Rooms  
3. YWCA, YMCA, YWHA, YMHA, PAL 
4. Beach Club 
5. Community Center 
6. Amusement Place, Bathhouse, Boat House 
7. Museum 
8. Library  
9. Miscellaneous  
 
Q. OUTDOOR RECREATION FACILITIES 
0. Open Space 
1. Parks/Recreation Facilities  
2. Playground 
3. Outdoor Pool 
4. Beach 
5. Golf Course 
6. Stadium, Race Track, Baseball Field 
7. Tennis Court 
8. Marina, Yacht Club 
9. Miscellaneous 
G.  Community Gardens 
 
R. CONDOMINIUMS 
0. Condo Billing Lot 
1. Residential Unit in 2-10 Unit Bldg 
2. Residential Unit in Walk-Up Bldg 
3. Residential Unit in 1-3 Story Bldg 
4. Residential Unit in Elevator Bldg 
5. Miscellaneous Commercial 
6. Residential Unit of 1-3 Unit Bldg-Orig Class 1 
7. Commercial Unit of 1-3 Unit Bldg-Orig Class 
1 
8. Commercial Unit of 2-10 Unit Bldg  
9. Co-op within a Condominium 
A Cultural, Medical, Educational, etc. 
B  Office Space 
C Commercial Building (Mixed Commercial 
Condo Building Classification Codes) 
D Residential Building (Mixed Residential 
Condo Building Classification Codes) 
G  Indoor Parking 
H Hotel/Boatel 
I Mixed Warehouse/Factory/Industrial & 
Commercial 
K Retail Space 
M Mixed Residential & Commercial Building 
(Mixed Residential & Commercial) 
P Outdoor Parking 
R Condominium Rentals 
S Non-Business Storage Space 
T Terraces/Gardens/Cabanas 
W Warehouse/Factory/Industrial 
X Mixed Residential, Commercial & Industrial 
Z Mixed Residential & Warehouse 
 
S. RESIDENCE - MULTIPLE USE 
0. Primarily One Family with Two Stores or 
Offices 
1. Primarily One Family with One Store or Office 
2. Primarily Two Family with One Store or 
Office 
3. Primarily Three Family with One Store or 
Office 
4. Primarily Four Family with One Store or 
Office 
5. Primarily Five to Six Family with One Store or 
Office 
9. Single or Multiple Dwelling with Stores or 
Offices 
T. TRANSPORTATION FACILITIES 
(ASSESSED IN ORE) 
1. Airport, Air Field, Terminal 
2. Pier, Dock, Bulkhead 
9. Miscellaneous 
 
U. UTILITY BUREAU PROPERTIES 
0. Utility Company Land and Building 
1. Bridge, Tunnel, Highway 
2. Gas or Electric Utility  
3. Ceiling Railroad 
4. Telephone Utility 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
52  
5. Communications Facilities Other Than 
Telephone 
6. Railroad - Private Ownership 
7. Transportation - Public Ownership 
8. Revocable Consent 
9. Miscellaneous  
 
V. VACANT LAND 
0. Zoned Residential; Not Manhattan 
1. Zoned Commercial or Manhattan Residential 
2. Zoned Commercial Adjacent to Class 1 
Dwelling; Not Manhattan 
3. Zoned Primarily Residential; Not Manhattan 
4. Police or Fire Department 
5. School Site or Yard 
6. Library, Hospital or Museum 
7. Port Authority of NY and NJ 
8. New York State & U.S. Government 
9. Miscellaneous 
 
W. EDUCATIONAL STRUCTURES 
1. Public Elementary, Junior or Senior High 
2. Parochial School, Yeshiva 
3. School or Academy 
4. Training School 
5. City University 
6. Other College and University 
7. Theological Seminary 
8. Other Private School 
9. Miscellaneous 
 
Y. SELECTED GOVERNMENT 
INSTALLATIONS 
(Excluding Office Buildings, Training Schools, 
Academic, Garages, Warehouses, Piers, Air 
Fields, Vacant Land, Vacant Sites, and Land 
Under Water and Easements) 
1. Fire Department 
2. Police Department 
3. Prison, Jail, House of Detention 
4. Military and Naval Installation 
5. Department of Real Estate 
6. Department of Sanitation 
7. Department of Ports and Terminals 
8. Department of Public Works 
9. Department of Environmental Protection 
 
 
 
Z. MISCELLANEOUS 
0. Tennis Court, Pool, Shed, etc.  
1. Court House 
2. Public Parking Area 
3. Post Office 
4. Foreign Government 
5. United Nations 
7. Easement 
8. Cemetery 
9. Other 
PLUTO DATA DICTIONARY January 2026 (25v4) 
 
53 
 
APPENDIX D:  LAND USE CATEGORIES 
 
 
DCP 
LAND 
USE 
CODE 
 
DCP LAND 
USE 
CATEGORIES 
 
DOF/DCP BUILDING CLASSES 
 
01 
 
One & Two 
Family Buildings 
 
A*,B*,Z0 
 
02 
 
Multi-Family 
Walk-Up 
Buildings 
 
C0,C1,C2,C3,C4,C5,C6,C8,C9, CM, R1,R2,R3,R6 
 
03 
 
Multi-Family 
Elevator 
Buildings 
 
D0,D1,D2,D3,D4,D5,D8,D9,H6,H7,R4,RD 
 
04 
 
Mixed 
Residential & 
Commercial 
Buildings 
 
C7,D6,D7,K4,O8,R8,R9,RM,RR,RX,RZ,S* 
 
05 
 
Commercial & 
Office Buildings 
 
G8,GU,GW,H1,H2,H3,H4,H5,H9,HB,HH,HR,HS,J*,K1,K2,K3,K5,K6, 
K7,K8,K9,O1,O2,O3,O4,O5,O6,O7,O9,P1,R5,R7,RB,RC,RH,RI,RK,RS  
 
06 
 
Industrial & 
Manufacturing 
Buildings 
 
E*,F*,L*,RW 
 
07 
 
Transportation & 
Utility 
 
G2,G3,G4,G5,G9,T*,U*,Y6,Y7,Y8,Y9 
 
08 
 
Public Facilities 
& Institutions 
 
H8,I*,M*,N*,P2,P3,P5,P7,P8,P9,RA,W*,Y1,Y2, 
Y3,Y4,Z1,Z3,Z4,Z5 
 
09 
 
Open Space & 
Outdoor 
Recreation 
  
P4,P6,Q*,Z8 
 
10 
 
Parking Facilities 
 
G0,G1,G6,G7,RG,RP,Z2 
 
11 
 
Vacant Land 
 
V* 
 
 
 
NOTES: * Denotes all DOF/DCP Building Class classifications within an alphabetic grouping. 
The Building Classes R0, Y5, Z7, and Z9 are not assigned to a Land Use Category. 
 