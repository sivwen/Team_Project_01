import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
import re
import time
from time import sleep
from openpyxl import load_workbook
import cx_Oracle

# 한글 폰트 설정
font_path = 'C:\\Windows\\Fonts\\malgun.ttf'  # 필요한 폰트 파일 경로
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="뮤지컬 《시카고》",
    layout="wide",
)

# 스타일 적용을 위한 CSS
st.markdown("""
    <style>
        .header, .footer {
            text-align: center; 
            padding: 10px; 
        }
        .header {
            background-color: #DF0101; 
        }
        .footer {
            background-color: lightgray;
            position: fixed; 
            bottom: 0; 
            width: 100%;
        }
        .section {
            background-color: #f0f0f0; 
            padding: 10px;
            margin: 10px 0;
            text-align: center;
        }
        table {
            border: 1px #a39485 solid;
            font-size: .9em;
            box-shadow: 0 2px 5px rgba(0,0,0,.25);
            width: 100%;
            border-collapse: collapse;
            border-radius: 5px;
            overflow: hidden;
        }
        h2 {
            color : #FFFFFF;
        }
        th, td {
            border: 1px solid black;
            padding: 5px;
            text-align: center;
            background-color: #FFFFFF;
        }
        th {
            background-color: #dddddd;
        }
    </style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("<div class='header'><h2>뮤지컬 《시카고》</h2></div>", unsafe_allow_html=True)

container = st.container()
container2 = st.container()

with container:
    # 본문 레이아웃
    col1, col2, col3 = st.columns([2,3,1])

    # csv data
    review = pd.read_csv('chicago_review_emp.csv', encoding='cp949')
    # 왼쪽 사이드바
    with col1:
        st.image("http://www.kopis.or.kr/upload/pfmPoster/PF_PF239123_240412_145134.jpg")
        casting = pd.read_csv("시카고_캐스팅_240903.csv", encoding="cp949")
        casting = casting.iloc[:, 1:]
        st.table(casting)

    # 가운데 컨텐츠
    with col2:
        st.markdown("<div class='section'><h4>관람후기</h4>", unsafe_allow_html=True)
        review.drop('Unnamed: 0', axis=1, inplace=True)
        review.columns = ['날짜', '평점', '관람후기']
        st.table(review.head(5))

        blog = load_workbook("시카고_블로그_크롤링.xlsx")

        sheet = blog.active

        # 시트의 데이터를 DataFrame으로 변환
        data = sheet.values
        columns = next(data)[0:]  # 첫 번째 행을 열 이름으로 사용
        df = pd.DataFrame(data, columns=columns)
        df = df[['주소','제목']]

        # 데이터프레임을 Streamlit 테이블로 출력
        st.markdown("<div class='section'><h4>네이버 블로그</h4>", unsafe_allow_html=True)
        st.dataframe(df,use_container_width=True)

    # 오른쪽 사이드바
    with col3:
        url = "https://tickets.interpark.com/goods/24005266"
        options = Options()
        options.add_experimental_option("detach", True)
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")  # GPU 비활성화 (Linux에서 필요할 수 있음)
        options.add_argument("--window-size=1920,1080")  # 화면 크기 설정

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        popup = driver.find_element(By.CSS_SELECTOR, 'div.popupCheck > a.popupCheckLabel')
        popup.click()
        time.sleep(1)
        review_click = driver.find_element(By.CSS_SELECTOR, 'a[data-target="REVIEW"]')
        review_click.click()

        musical_review_score = driver.find_element(By.CSS_SELECTOR, 'div.prdStarScore')
        ttl_score = musical_review_score.text.strip().replace('\n', '')

        review_score = round((review['평점'].mean()) * 2, 1)
        st.markdown(f'#### :star:{ttl_score}')
        st.markdown(f'#### :heart:관객 평점 : {review_score}')
st.markdown("""
    <style>
    #container2 .streamlit-col1 {
        padding: 0 5px; /* Adjust the left and right padding */
        margin-left: 0;
        margin-right: 0;
    }
    #container2 .streamlit-col2 {
        padding: 0 5px;
        margin-left: 0;
        margin-right: 0;
    }
    #container2 .streamlit-container {
        margin-left: 0;
        margin-right: 0;
    }
    </style>
""", unsafe_allow_html=True)

with container2:
    col1, col2 ,col3 = st.columns([1,1,4],gap="small")
    @st.cache_data
    def get_data_from_oracle():
        connection = cx_Oracle.connect('open_source/1111@192.168.0.18:1521/xe')
        query = '''
        SELECT t1.BASEDATE,
               t1.TITLE,
               t1.RANK,
               t1.FLUC_RANGE,
               coalesce(t2.GENRE_CODE, 4)as GENRE_CODE,
               coalesce(t2.GENRE, '데이터없음')as GENRE
        FROM rank_item_cluster t1
        LEFT JOIN musical_cluster t2
        ON replace(replace(REPLACE(t1.TITLE, ' ', ''), '젠', '잰'), '？','?') = REPLACE(t2.TITLE, ' ', '')
        '''
        df = pd.read_sql(query, con=connection)
        connection.close()
        return df


    def get_all_titles(df):
        title_counts = df['TITLE'].value_counts()
        top_titles_df = title_counts.reset_index()
        top_titles_df.columns = ['Title', 'Frequency']
        top_titles_df['추천 순위'] = range(1, len(top_titles_df) + 1)
        top_titles_df = top_titles_df[['추천 순위', 'Title', 'Frequency']]
        top_titles_df.columns = ['추천 순위', '제목', 'Top5 빈도 수']  # Rearrange columns
        return top_titles_df


    def get_titles_by_genre(df, title):
        # Step 1: Get the genre_code for the specific title
        genre_code = df[df['TITLE'] == title]['GENRE_CODE'].iloc[0]

        # Step 2: Filter rows with the same genre_code
        filtered_df = df[df['GENRE_CODE'] == genre_code]

        # Exclude the specified title
        filtered_df = filtered_df[filtered_df['TITLE'] != title]

        # Step 3: Count the frequency of each title in the filtered DataFrame
        title_counts = filtered_df['TITLE'].value_counts().reset_index()
        title_counts.columns = ['제목', '빈도 수']

        # Step 4: Sort by frequency in descending order
        sorted_titles_df = title_counts.sort_values(by='빈도 수', ascending=False).reset_index(drop=True)

        # Add a ranking column
        sorted_titles_df['추천 순위'] = range(1, len(sorted_titles_df) + 1)

        # Reorder columns
        sorted_titles_df = sorted_titles_df[['추천 순위', '제목', '빈도 수']]

        return sorted_titles_df

    # df = get_data_from_oracle()
    #
    # # Filter for the specified title and display titles of the same genre, sorted by frequency
    # title = '시카고'
    # sorted_titles_by_genre = get_titles_by_genre(df, title)
    #
    # st.dataframe(sorted_titles_by_genre,hide_index=True)
    #

    def get_top_5_recommendations(csv_path):
        # Read the ranking CSV with the correct encoding
        ranking_df = pd.read_csv(csv_path, encoding='cp949')

        # Check column names

        # Manually specify top 5 based on the CSV file order
        top_5 = ranking_df.head(10)

        # Return the top 5 recommendations
        return top_5[['rank', 'title']]

    with col1:

        df = get_data_from_oracle()
        st.markdown('뮤지컬 추천 - 코사인 유사도 기반')
        # Path to your CSV file with ranking data
        csv_path = '시카고_코사인유사도_결과.csv'
        top_5_recommendations = get_top_5_recommendations(csv_path)

    # Rename columns for display
        top_5_recommendations.columns = ['순위', '제목']

        st.dataframe(top_5_recommendations, hide_index=True)

    with col2:

        title = '시카고'
        sorted_titles_by_genre = get_titles_by_genre(df, title)

        st.markdown('뮤지컬 추천 - 클러스터 빈도 수 기반')
        st.dataframe(sorted_titles_by_genre,hide_index=True)