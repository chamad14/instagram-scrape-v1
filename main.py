from playwright.sync_api import sync_playwright
import time
import json

USERNAME = 'your IG username'
PASSWORD = 'your IG password'

def login_to_instagram(page):
    try:
        page.goto('https://www.instagram.com/')
        time.sleep(5)
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.press('input[name="password"]', 'Enter')
        page.wait_for_selector('text=Home', timeout=10000)
    except Exception as e:
        print(f"An error occurred during login: {e}")

def get_followers_or_following(page, username, follow_type='followers'):
    follow_list = []
    try:
        page.goto(f'https://www.instagram.com/{username}')
        time.sleep(5)
        follow_button = page.locator(f'//div/div/div[2]/div/div/div[1]/div[2]/div/div[1]/section/main/div/header/section[3]/ul/li[{2 if follow_type == "followers" else 3}]/div/a')
        follow_button.click()
        page.wait_for_selector('div.x9f619.x1n2onr6.x1ja2u2z.x78zum5.x1iyjqo2.xs83m0k.xeuugli.x1qughib.x6s0dn4.x1a02dak.x1q0g3np.xdl72j9 > div > div > div > div > div > a > div > div', timeout=10000)
        time.sleep(30)
        follow_div = page.locator('div.x9f619.x1n2onr6.x1ja2u2z.x78zum5.x1iyjqo2.xs83m0k.xeuugli.x1qughib.x6s0dn4.x1a02dak.x1q0g3np.xdl72j9 > div > div > div > div > div > a > div > div')
        follow_list = follow_div.all_text_contents()
    except Exception as e:
        print(f"An error occurred while getting {follow_type}: {e}")
    return follow_list

def intercept_likers_request(page, username, max_posts=50):
    posts_data = []
    
    def handle_response(response):
        if 'likers/' in response.url:
            try:
                json_response = response.json()
                likers = json_response.get('users', [])
                total_likes = len(likers)
                likers_usernames = [liker['username'] for liker in likers]
                posts_data[-1]['likes'] = total_likes
                posts_data[-1]['likers'] = likers_usernames
            except Exception as e:
                print(f"Error processing likers response: {e}")

    page.on('response', handle_response)

    try:
        page.goto(f'https://www.instagram.com/{username}')
        time.sleep(5)

        post_elements = page.locator('//div/div/div/div/div/div/div/div/div/section/main/div/div/div/div/div/a')
        post_count = min(post_elements.count(), max_posts)

        for i in range(post_count):
            post_elements.nth(i).click()
            page.wait_for_selector('article div div span a', timeout=10000)
            time.sleep(8)
            
            posts_data.append({
                'username': username,
                'post_number': i + 1,
                'likes': 0,
                'likers': []
            })

            likes_button = page.locator('//html/body/div/div/div/div/div/div/div/div/div/div/article/div/div/div/div/div/section/div/div/span/a/span')
            likes_button.click()
            time.sleep(20)
            
            page.go_back()
            time.sleep(2)
    except Exception as e:
        print(f"An error occurred while getting posts and likes: {e}")

    return posts_data

def find_mutuals(followers_1, following_1, followers_2, following_2):
    mutual_followers = set(followers_1) & set(followers_2)
    mutual_following = set(following_1) & set(following_2)
    return list(mutual_followers), list(mutual_following)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        login_to_instagram(page)
        
        usernames = ['user1', 'user2']  # Add the Instagram usernames you want to scrape

        # Get followers and following for both accounts
        followers_1 = get_followers_or_following(page, usernames[0], 'followers')
        following_1 = get_followers_or_following(page, usernames[0], 'following')
        followers_2 = get_followers_or_following(page, usernames[1], 'followers')
        following_2 = get_followers_or_following(page, usernames[1], 'following')

        # Find mutuals
        mutual_followers, mutual_following = find_mutuals(followers_1, following_1, followers_2, following_2)

        all_likers_data = {
            'profiles': {
                usernames[0]: {
                    'followers': followers_1,
                    'following': following_1
                },
                usernames[1]: {
                    'followers': followers_2,
                    'following': following_2
                }
            },
            'mutual_followers': mutual_followers,
            'mutual_following': mutual_following,
            'mutual_likers_data': {}
        }

        # Scrape likes for mutual followers
        for mutual_follower in mutual_followers:
            print(f"Scraping data for mutual follower: {mutual_follower}")
            likers_data = intercept_likers_request(page, mutual_follower)
            all_likers_data['mutual_likers_data'][mutual_follower] = likers_data

        # Scrape likes for mutual following
        for mutual_follow in mutual_following:
            print(f"Scraping data for mutual following: {mutual_follow}")
            likers_data = intercept_likers_request(page, mutual_follow)
            all_likers_data['mutual_likers_data'][mutual_follow] = likers_data
        
        # Save the scraped data
        with open('all_likers_data.json', 'w') as f:
            json.dump(all_likers_data, f, indent=4)
        
        browser.close()
