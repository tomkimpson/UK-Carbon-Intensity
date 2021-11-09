import streamlit as st
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns


from datetime import datetime, date 
import requests
import json

import altair as alt
import dateutil.parser as parser 



#



def plot_line(df):


    xval,yval,xlabel, ylabel = 'time:T','carbon_intensity:Q','Time', 'Carbon Intensity (g/kWh)'


    #Plot the line of datetime vs carbon intensity
    line = alt.Chart(df).mark_line(interpolate='basis').encode(
        x=alt.X(xval,axis=alt.Axis(title=xlabel)),
        y=alt.X(yval,axis=alt.Axis(title=ylabel))
    )



    nearest = alt.selection(type='single', nearest=True, on='mouseover',
                            fields=['time_float'], empty='none')




    selectors = alt.Chart(df).mark_point().encode(
        x=xval,
        opacity=alt.value(0),
    ).add_selection(
        nearest
    )

    # Draw points on the line, and highlight based on selection
    points = line.mark_point().encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    )

    # Draw text labels near the points, and highlight based on selection
    text = line.mark_text(align='left', dx=5, dy=-5).encode(
        text=alt.condition(nearest, yval, alt.value(' '))
    )

    # Draw a rule at the location of the selection
    rules = alt.Chart(df).mark_rule(color='gray').encode(
        x=xval,
    ).transform_filter(
        nearest
    )


    c = alt.layer(
        line,selectors,points,rules,text
    ).properties(
        width=730, height=400
    )


    st.altair_chart(c)


def plot_area_chart(df):

    #xval = 't_norm'
    #xval = 't_datetime'
    xlabel = 'Time [s]'
    ylabel = '%'
    x = 't_norm'
    x = 't_datetime'

    leg_selection = alt.selection_multi(fields=['fuel'], bind='legend')

    # The basic line
    line = alt.Chart(df).mark_area(interpolate='basis',clip=True).encode(
        x=alt.X(x,scale=alt.Scale(nice=False),axis=alt.Axis(tickCount=5,title=xlabel)),
        y=alt.X('perc',scale=alt.Scale(domain=(0,100)),axis=alt.Axis(title=ylabel),stack=True),
        color='fuel',
        opacity=alt.condition(leg_selection, alt.value(1), alt.value(0.2)),
        tooltip = [alt.Tooltip(x, title='Time'), alt.Tooltip('fuel', title='Fuel'),alt.Tooltip('perc', title='Percentage')]
    ).add_selection(leg_selection)



    # Put the five layers into a chart and bind the data
    c = alt.layer(
        line #,selectors #,rules,text
    ).properties(
        width=730, height=400
    )

    st.altair_chart(c)


@st.cache()
def fetch_carbon_intensity_data(t1,t2):

    #Fetch data from API
    headers = {
      'Accept': 'application/json'
    }
 


    mix = requests.get('https://api.carbonintensity.org.uk/intensity/{}/{}'.format(t1, t2), params={}, headers = headers)
    mix = mix.json()
    data_nested = mix['data']
    carbon_df = pd.json_normalize(data_nested) 
    carbon_df = carbon_df.rename(columns={'intensity.actual': 'carbon_intensity'})


    carbon_df['time'] = pd.to_datetime(carbon_df['from'])
    carbon_df['time_float'] = carbon_df['time'].apply(lambda d: d.timestamp())

    return carbon_df


@st.cache()
def fetch_energy_source_type_data(t1,t2):

    headers = {
      'Accept': 'application/json'
    }


    mix = requests.get('https://api.carbonintensity.org.uk/generation/{}/{}'.format(t1, t2), params={}, headers = headers)
    mix = mix.json()


    #mix

    data_nested = mix['data']
    df = pd.json_normalize(data_nested) #,record_path = 'generationmix')
    df = pd.concat([pd.DataFrame(x) for x in df['generationmix']], keys=df['from']).reset_index(level=1, drop=True).reset_index()
    df["t_datetime"] = df["from"].apply(parser.parse,ignoretz=True) #convert from ISO format to datetime
    df["t_sec"] =  (df["t_datetime"] - pd.Timestamp("1970-01-01"))// pd.Timedelta("1ms") #milliseconds since epoch. https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#from-timestamps-to-epoch
    df["t_norm"] = (df["t_sec"] - min(df["t_sec"])) / 1e3 #time normalised w.r.t initial value
    df["t_norm_min"] = df["t_norm"] / 60
    df["t_norm_hr"] = df["t_norm_min"] / 60
    df["fuel"] = df["fuel"].str.capitalize()


    return df

@st.cache()
def fetch_source_carbon_intensity_numbers():

    headers = {
      'Accept': 'application/json'
    }
 
    r = requests.get('https://api.carbonintensity.org.uk/intensity/factors', params={}, headers = headers) 
    r = r.json()



    df = pd.json_normalize(r['data']).T
    df.columns = ['Carbon Intensity']


   #df.sort_values('Carbon Intensity')

    
    return df.sort_values('Carbon Intensity', ascending=False) 

def FAQ():
    expander = st.beta_expander("FAQ")

    expander.write("**How do you determine the Carbon Intensity numbers?**")
    expander.write("The National Grid ESO, in partnership with the Environmental Defence Fund Europe, the University of Oxford Department of Computer Science and the WWF have provided a very useful API. Please see https://carbonintensity.org.uk")

    expander.write("**How was this website created?**")
    expander.write("Using a combination of [Python](https://www.python.org), [Streamlit](https://streamlit.io), [Altair](https://altair-viz.github.io/getting_started/overview.html), and [Heroku](https://www.heroku.com)")





def main():

    #Config
    st.set_page_config(page_title = 'UK Carbon Intensity',page_icon=":shark:",layout="centered", initial_sidebar_state="collapsed")



    default_start_date = datetime(2021, 1, 1)
    default_end_date = datetime(2021, 1, 2)

    d3 = st.sidebar.date_input("Choose your time range", value =[default_start_date,default_end_date],max_value=date.today())
    t1 = d3[0].isoformat()
    t2 = d3[1].isoformat()
    

    #Into text
    st.title('What is the Carbon Intensity of the UK National Grid?')

    st.write('[Carbon Intensity](https://en.wikipedia.org/wiki/Emission_intensity) describes the quantity of CO$_2$ emitted per unit energy generated.')

    st.write('Typical fuels such as coal or gas have **high** carbon intensities, whilst carbon zero fuels such as solar or nuclear energy have carbon intensities values of **zero**')


    st.write('The National Grid provides electricity using a combination of different energy sources. This combination changes over time; for example on windy days more electricity is generated using wind power, rather than burning natural gas. Consequently the mean carbon intensity of the grid changes from day to day and month to month.')

    st.write('This tool provides an interface for determining the **carbon intensity** and the breakdown by **energy source** at a particular time.')
    
    st.write('**Please choose a time range from the sidebar.**')

    st.header('Carbon Intensity Time Series')

    #Grab some numbers for the carbon intensity over time
    carbon_df = fetch_carbon_intensity_data(t1,t2)
   
    #st.write(carbon_df.drop('intensity.forecast',axis=1))

    #Plot it up 
    plot_line(carbon_df)



    st.header('Energy Source Type')

    #Grab some numbers for energy source type over time 
    energy_type_df =  fetch_energy_source_type_data(t1,t2)



    #Plot this up too
    plot_area_chart(energy_type_df)





    #FAQ
    FAQ()


    #Grab some example numbers 
    CI_df = fetch_source_carbon_intensity_numbers()
    expander = st.beta_expander("Appendix")
    expander.write('The carbon intensity values by fuel source are as follows:')
    expander.write(CI_df)



if __name__ == '__main__':
    main()
