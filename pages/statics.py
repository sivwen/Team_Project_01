import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
import time

df = pd.read_csv('통계자료_전체_공연.csv',encoding='cp949')

st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 80%; /* 화면의 80% 너비 */
        # padding-top: 0rem; 
        padding-right: 0rem; 
        padding-left: 0rem; 
        # padding-bottom: 0rem; 
        margin: 0 auto; /* 중앙 정렬 */
    }
    </style>
    """,
    unsafe_allow_html=True
)

basedates = df['basedate'].unique()
st.title('공연 통계 데이터')
placeholder = st.empty()

color_map = {
    '연극': 'blue',
    '뮤지컬': 'green',
    '서양음악(클래식)': 'red',
    '한국음악(국악)': 'purple',
    '대중음악': 'orange',
    '무용(서양/한국무용)': 'pink',
    '대중무용': 'cyan',
    '서커스/마술': 'magenta',
    '복합': 'grey'
}

while True:
    for date in basedates:
        with placeholder.container():
            # Filter data for the specific 'basedate'
            df_filtered = df[df['basedate'] == date]

            # Create pie charts using Plotly
            fig1 = px.pie(df_filtered, values='nmrsshr', names='cate', color='cate', color_discrete_map=color_map,
                          title=f'관객 점유율 {date}')
            fig2 = px.pie(df_filtered, values='amountshr', names='cate', color='cate', color_discrete_map=color_map,
                          title=f'티켓판매액 점유율 {date}')

            # Create 3 columns
            col1, col2, col3 = st.columns(3)

            # Display the pie charts in the first two columns
            with col1:
                # File path to the PNG image
                file_path1 = '티켓 취소량 예측 결과물.png'
                file_path2 = '티켓 예매량 예측 결과물.png'
                # Display the image
                st.image(file_path1, caption='티켓 취소량 예측', use_column_width=True)
                st.image(file_path2, caption='티켓 예매량 예측', use_column_width=True)

            with col2:
                st.plotly_chart(fig1)

            # Example content in col3
            with col3:
                st.plotly_chart(fig2)
        # Wait for 5 seconds before moving to the next 'basedate'
        time.sleep(5)