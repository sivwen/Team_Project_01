import streamlit as st
import requests
import cx_Oracle
import xml.etree.ElementTree as ET
import folium
from folium.plugins import MarkerCluster
from datetime import datetime, timedelta
from streamlit_folium import st_folium
from geopy.distance import great_circle
from shapely.geometry import Point, box
import pandas as pd
import time
import re

# Ensure you have a valid API key
api_key = '648094eb74c149b5856d56c4cac9ec62'
@st.cache_data
def get_request_url(stdate, eddate, prfstate, kidstate):
    params = {
        'service': api_key,
        'cpage': 1,
        'rows': 300,
        'stdate': stdate,
        'eddate': eddate,
        'shcate': 'GGGA',
        'kidstate': kidstate,
        'prfstate': prfstate
    }
    api_url = 'http://kopis.or.kr/openApi/restful/pblprfr'
    response = requests.get(api_url, params=params)
    return response.content


def performance_request():
    response = get_request_url(stdate, eddate, prfstate, kidstate)
    root = ET.fromstring(response)

    performances = []
    missing_coordinates = []

    for item in root.findall(".//db"):
        facility_name = item.find('fcltynm').text if item.find('fcltynm') is not None else ""
        performance_name = item.find('prfnm').text if item.find('prfnm') is not None else ""
        mt20id = item.find('mt20id').text if item.find('mt20id') is not None else ""
        prfpdfrom = item.find('prfpdfrom').text if item.find('prfpdfrom') is not None else ""
        prfpdto = item.find('prfpdto').text if item.find('prfpdto') is not None else ""
        performances.append({
            'mt20id': mt20id,
            'fcltynm': facility_name,
            'prfnm': performance_name,
            'prfpdfrom': prfpdfrom,
            'prfpdto': prfpdto
        })
    return performances, missing_coordinates
def get_request_detail_url(mt20id):
    params = {
        'service': api_key,
    }
    api_url = f'http://www.kopis.or.kr/openApi/restful/pblprfr/{mt20id}'
    response = requests.get(api_url, params=params)
    return response.content

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
def get_top_titles(df):
    title_counts = df['TITLE'].value_counts().head(5)
    top_titles_df = title_counts.reset_index()
    top_titles_df.columns = ['Title', 'Frequency']
    top_titles_df['추천 순위'] = range(1, len(top_titles_df) + 1)
    top_titles_df = top_titles_df[['추천 순위', 'Title', 'Frequency']]
    top_titles_df.columns = ['추천 순위','제목','Top5 빈도 수']# Rearrange columns
    return top_titles_df

@st.cache_data
def get_coordinates_and_facilities(venue_name):
    try:
        connection = cx_Oracle.connect('open_source/1111@192.168.0.18:1521/xe')
        cursor = connection.cursor()

        query = """
        SELECT la, lo, restaurant, cafe, store, nolibang, suyu,
               parkbarrier, restbarrier, runwbarrier, elevbarrier, parkinglot
        FROM locate
        WHERE fcltynm = :venue_name
        """
        cursor.execute(query, {'venue_name': venue_name})
        result = cursor.fetchone()
        return result
    except cx_Oracle.DatabaseError as e:
        error, = e.args
        return None
    finally:
        if 'connection' in locals():
            connection.close()

def search_youtube_videos(query, num_videos=3):
    # Selenium options for headless browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    # Search YouTube
    search_url = f"https://www.youtube.com/results?search_query={query}"
    driver.get(search_url)

    # Wait for page to load
    # time.sleep(1)  # Wait for sufficient time for the page to load

    # Find video elements
    video_elements = driver.find_elements(By.XPATH, '//*[@id="video-title"]')

    video_urls = []
    for element in video_elements[:num_videos]:
        video_url = element.get_attribute('href')
        if video_url:
            video_urls.append(video_url)

    driver.quit()
    return video_urls
# Date calculation
today = datetime.now()
next_month = today + timedelta(days=30)
last_month = today - timedelta(days=365)

stdate = last_month.strftime('%Y%m%d')
eddate = next_month.strftime('%Y%m%d')

# Initialize session state variables if not already set
if 'prfstate' not in st.session_state:
    st.session_state.prfstate = '01'  # Default: 공연중
if 'kidstate' not in st.session_state:
    st.session_state.kidstate = 'N'  # Default: 전부

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

static_link = 'statics'
static_name = '뮤지컬 통계 정보'
# st.title('뮤지컬 통합 정보 화면')
# st.markdown(f"[{static_name}]({static_link})")
st.markdown(
    """
    <style>
    .centered {
        display: flex;
        flex-direction: column; /* 세로 방향으로 정렬 */
        justify-content: center;
        align-items: center;
        text-align: center;
        margin-top: 50px; /* 상단 여백 설정 */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 중앙에 배치할 콘텐츠
st.markdown(
    f"""
    <div class="centered">
        <h1>Musi-Pass(뮤지패스)</h1>
        <a href="{static_link}">{static_name}</a>
    </div>
    """,
    unsafe_allow_html=True
)
# Create a container to use the full width of the page
with st.container():
    col1, col2, col3, col4 = st.columns([3, 3, 2, 2], gap="large")  # Use a container for full width and set gap to 'large' for better spacing

    # Left column for dataframe

    # Central column for map and performance info
    with col2:
        # st.title('뮤지컬 공연 정보 지도')
        st.markdown("<h3 class='center-text'>뮤지컬 공연 정보 지도</h3>", unsafe_allow_html=True)

        prfstate_options = {'공연중': '02', '공연예정': '01'}
        selected_state = st.selectbox('공연 상태 선택', options=list(prfstate_options.keys()), index=list(prfstate_options.values()).index(st.session_state.prfstate))
        prfstate = prfstate_options[selected_state]

        kidstate_options = {'아동 공연': 'Y', '전부': 'N'}
        selected_kidstate = st.selectbox('아동 공연 여부 선택', options=list(kidstate_options.keys()), index=list(kidstate_options.values()).index(st.session_state.kidstate))
        kidstate = kidstate_options[selected_kidstate]

        # Sidebar for error messages
        # error_messages = st.sidebar

        # API request and XML parsing

        performances, missing_coordinates = performance_request()
        map = folium.Map(location=[36.5, 127.5], zoom_start=7)

        # Initialize the MarkerCluster
        marker_cluster = MarkerCluster().add_to(map)

        # Retrieve coordinates and add markers to the map
        bounds = []  # List to store coordinates within bounds

        for performance in performances:
            venue_name = performance['fcltynm']
            performance_name = performance['prfnm']

            coordinates_and_facilities = get_coordinates_and_facilities(venue_name)

            if coordinates_and_facilities:
                lat, lon = coordinates_and_facilities[0], coordinates_and_facilities[1]

                # Check if coordinates are valid
                if lat and lon:
                    bounds.append([lat, lon])  # Add to bounds list

                    # Add marker to the cluster
                    folium.Marker(
                        location=[lat, lon],
                        # HTML을 사용하여 팝업 내용 정의 (이름들을 가로로 정렬)
                        popup=folium.Popup(
                            f"""
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <b>{performance_name}</b>
                                <b>{venue_name}</b>
                            </div>
                            """,
                            max_width=300
                        ),
                        tooltip=f'<b>{venue_name}',
                        icon=folium.Icon(color='blue', icon='bookmark')
                    ).add_to(marker_cluster)
                # else:
                    # missing_coordinates.append(venue_name)
            # else:
                # missing_coordinates.append(venue_name)

        # Display the map
        map_display = st_folium(map, height=600, width=800)
    with col3:
        # st.title('공연 상세 정보')
        st.markdown("<h3 class='center-text'>공연 상세 정보</h3>", unsafe_allow_html=True)
        # Display information about the clicked marker
        if map_display and map_display.get('last_object_clicked_tooltip'):
            clicked_name = map_display['last_object_clicked_tooltip']

            for performance in performances:
                if performance['fcltynm'] == clicked_name:
                    coordinates_and_facilities = get_coordinates_and_facilities(clicked_name)
                    nearest_facilities = coordinates_and_facilities
                    nearest_performance = performance
                    break
            if nearest_performance:
                linked_name = nearest_performance['prfnm']
                linked_link = f"/{linked_name.replace(' ', '_').replace('[', '').replace(']', '').replace('(', '&#40;').replace(')', '&#41;')}"
                st.write(f"**공연 이름**: [{linked_name}]({linked_link})")
                st.write(f"**공연장**: {nearest_performance['fcltynm'].replace('[', '&#91;').replace(']', '&#93;').replace('(', '&#40;').replace(')', '&#41;')}")
                st.write(f"**시작일**: {nearest_performance['prfpdfrom']}")
                st.write(f"**종료일**: {nearest_performance['prfpdto']}")
                facilities = {
                    '레스토랑': 'O' if nearest_facilities[2] == 'Y' else 'X',
                    '카페': 'O' if nearest_facilities[3] == 'Y' else 'X',
                    '편의점': 'O' if nearest_facilities[4] == 'Y' else 'X',
                    '놀이방': 'O' if nearest_facilities[5] == 'Y' else 'X',
                    '수유실': 'O' if nearest_facilities[6] == 'Y' else 'X',
                    '장애시설-주차장': 'O' if nearest_facilities[7] == 'Y' else 'X',
                    '장애시설-화장실': 'O' if nearest_facilities[8] == 'Y' else 'X',
                    '장애시설-경사로': 'O' if nearest_facilities[9] == 'Y' else 'X',
                    '장애시설-엘리베이터': 'O' if nearest_facilities[10] == 'Y' else 'X',
                    '주차시설': 'O' if nearest_facilities[11] == 'Y' else 'X'
                }

                st.write("**시설 정보**:")
                for facility, available in facilities.items():
                    if available == 'O':
                        st.write(f"{facility}: 사용 가능")
            else:
                st.write("주어진 좌표와 가까운 공연 정보를 찾을 수 없습니다.")
        else:
            st.info("마커를 클릭하여 공연 정보를 확인하세요.")

        # Display missing coordinates in the sidebar
        # if missing_coordinates:
        #     error_messages.warning("아래의 장소가 표시되지 않습니다.")
        #     for venue in missing_coordinates:
        #         error_messages.write(f'{venue}')
    # Right column for YouTube embed
    with col4:
        import streamlit as st
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time



        if map_display and map_display.get('last_object_clicked_tooltip'):
            clicked_name = map_display['last_object_clicked_tooltip']

            for performance in performances:
                if performance['fcltynm'] == clicked_name:
                    # coordinates_and_facilities = get_coordinates_and_facilities(clicked_name)
                    # nearest_facilities = coordinates_and_facilities
                    nearest_performance = performance
                    break

            if nearest_performance:
                linked_name = nearest_performance['prfnm']
                search_query = f'뮤지컬 {linked_name}'
                # User input for search query
                # Streamlit app setup
                st.markdown("<h3 class='center-text'>관련 유튜브 검색</h3>", unsafe_allow_html=True)
                if search_query:
                    video_urls = search_youtube_videos(search_query, num_videos=3)

                    if video_urls:
                        st.write(f"{search_query} 검색 결과: ")

                        # Display videos in a 4x1 grid using rows
                        for url in video_urls:
                            st.video(url)
                    else:
                        st.write("No results found for your search.")

    with col1:

        # 데이터 로드

        # Load data
        df = get_data_from_oracle()

        # Convert 'basedate' to datetime format for better sorting
        df['BASEDATE'] = pd.to_datetime(df['BASEDATE'], format='%Y-%m-%d')

        # Sort DataFrame by 'basedate' and 'rank'
        df_sorted = df.sort_values(by=['BASEDATE', 'RANK'])

        # Filter columns
        df_filtered = df_sorted[['TITLE', 'RANK', 'FLUC_RANGE', 'GENRE_CODE']]

        # Define a color map for genre_code
        color_map = {
            0: 'background-color: lightblue;',
            1: 'background-color: lightgreen;',
            2: 'background-color: lightyellow;',
            3: 'background-color: lightcoral;',
            4: 'background-color: lightgray;'
        }


        # Apply the color map
        def color_genre_code(val):
            return color_map.get(val, '')


        # Format FLUC_RANGE
        def format_fluc_range(value):
            if value > 0:
                if value < 1000:
                    return f'🔺{value}'
                elif value == 1000:
                    return '🆕'
            elif value < 0:
                return f'🔽{-value}'
            else:
                return str(value)  # Ensure it is returned as a string


        # Get unique dates
        dates = df_sorted['BASEDATE'].unique()
        st.markdown("<h3 class='center-text'>추천 뮤지컬</h3>", unsafe_allow_html=True)

        placeholder_top5 = st.empty()

        top_titles_df = get_top_titles(df_sorted)
        placeholder_top5.dataframe(top_titles_df, hide_index=True)

        # Streamlit app
        st.markdown("<h3 class='center-text'>뮤지컬 실시간 순위</h3>", unsafe_allow_html=True)

        # Create a placeholder for the table
        # Create a placeholder for the main table
        placeholder_main = st.empty()

        # Create a placeholder for the top 5 titles table

        # Loop through dates and update the table every 5 seconds
        index = 0
        while True:
            if len(dates) == 0:
                st.write("No data available.")
                break

            date = dates[index]
            filtered_df = df_sorted[df_sorted['BASEDATE'] == date]
            filtered_df = filtered_df[['RANK', 'TITLE', 'FLUC_RANGE', 'GENRE_CODE', 'GENRE']].copy()
            filtered_df.columns = ['순위', '제목', '등락폭', '장르코드', '장르']
            filtered_df['등락폭'] = filtered_df['등락폭'].apply(format_fluc_range).astype(str)  # Ensure column is string type
            styled_df = filtered_df.style.map(color_genre_code, subset=['장르코드'])
            placeholder_main.dataframe(styled_df, hide_index=True)

            # Update the index and wait for 5 seconds
            index = (index + 1) % len(dates)
            time.sleep(5)