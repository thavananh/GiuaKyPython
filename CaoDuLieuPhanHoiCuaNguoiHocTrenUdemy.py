from math import log
import sqlite3
import csv
from unicodedata import category
from selenium.webdriver.common.by import By
import selenium.common.exceptions
from seleniumbase import Driver
from seleniumbase import BaseCase
from selenium import webdriver
import time
import re
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import tkinter as tk
from tkinter import messagebox, IntVar
from threading import Thread
from datetime import datetime
import threading

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.lock = threading.Lock()

    def connect(self):
        return sqlite3.connect(self.db_name)

    def execute(self, query, params=()):
        with self.lock:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            conn.close()

    def fetchall(self, query, params=()):
        with self.lock:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            return result

    def executemany(self, query, params=()):
        with self.lock:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.executemany(query, params)
            conn.commit()
            conn.close()

db = Database("CaoDuLieuUdemy.db")

def create_database():
    db.execute(
        """CREATE TABLE IF NOT EXISTS "UDEMYCOURSE" (
        "CourseId"    INTEGER,
        "CourseName"  TEXT NOT NULL,
        "CourseCategory"  TEXT NOT NULL,
        "CourseLink"  TEXT NOT NULL,
        PRIMARY KEY("CourseId" AUTOINCREMENT)
    );"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS "COMMENT" (
        "CommentId"   INTEGER,
        "Comment" TEXT,
        "course_id" INTEGER NOT NULL,
        PRIMARY KEY("CommentId" AUTOINCREMENT),
        FOREIGN KEY ("course_id") REFERENCES "UDEMYCOURSE" ("CourseId")
    );"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS CATEGORY (
            CategoryId         INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryName       TEXT NOT NULL,
            CategoryLink       TEXT NOT NULL,
            ParentId  INTEGER  REFERENCES CATEGORY(CategoryId)
            );"""
    )
    db.execute(
        """CREATE INDEX IF NOT EXISTS idx_category_parent ON CATEGORY(ParentId);"""
    )
    
    
def execute_return_id( query, params=()):
    """Chạy INSERT và trả về lastrowid"""
    with threading.Lock():
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

def insert_category_to_db(category_name, category_link, parent_id=None):
    return execute_return_id(
            "INSERT INTO CATEGORY (CategoryName, CategoryLink, ParentId) VALUES (?, ?, ?)",
            (category_name, category_link, parent_id)
    )

def get_categories_from_db():
    db.fetchall("SELECT CategoryName, CategoryLink FROM CATEGORY")

def insert_course_to_db(course_name, course_category, course_link):
    db.execute(
        "INSERT INTO UDEMYCOURSE (CourseName, CourseCategory, CourseLink) VALUES (?, ?, ?)",
        (course_name, course_category, course_link),
    )

def get_courses_from_db():
    return db.fetchall("SELECT CourseName, CourseCategory, CourseLink FROM UDEMYCOURSE")

def insert_comment_to_db(comments, course_name):
    course_id = db.fetchall(
        "SELECT CourseId FROM UDEMYCOURSE where CourseName = ?", (course_name,)
    )[0][0]
    db.executemany(
        "INSERT INTO COMMENT (Comment, course_id) VALUES (?, ?)",
        [(comment, course_id) for comment in comments],
    )

def is_course_in_db(course_link):
    result = db.fetchall(
        "SELECT 1 FROM UDEMYCOURSE WHERE CourseLink = ?", (course_link,)
    )
    return len(result) > 0

def log_message(message, text_box=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    if text_box:
        text_box.insert(tk.END, f"{formatted_message}\n")
        text_box.see(tk.END)

def get_category_links_from_main_page(text_box, headless=False):
    website = "https://www.udemy.com"
    category_links = []

    driver = Driver(
        uc=True,
        browser="chrome",
        locale_code="vi",
        headless=headless,
        window_size="1920, 1080",
    )
    driver.uc_open_with_reconnect(website, 4)

    # Mở menu chính
    main_category_button = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//nav[contains(@class, 'popper')]"))
    )
    main_category_button.click()
    log_message("Clicked main category", text_box)

    # Lấy danh sách parent category
    parent_category_buttons = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "(//nav[contains(@class,'popper')]//ul)[2]/li")
        )
    )

    actions = ActionChains(driver)
    for parent in parent_category_buttons:
        # Hover lên parent
        actions.move_to_element(parent).perform()
        log_message(f"Hovered vào parent: {parent.text}", text_box)
        
        parent_name = parent.text.strip()
        parent_link = parent.find_element(By.TAG_NAME, "a").get_attribute("href")
        # Lấy danh sách level-2 
        level_two_buttons = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//nav[contains(@class,'popper')]//div[contains(@id,'level-two')]//li/a")
            )
        )
        parent_id = insert_category_to_db(parent_name, parent_link, None)
        log_message(f"Inserted parent [{parent.text}] id={parent_id}", text_box)
        for lvl2 in level_two_buttons:
            lvl2_name = lvl2.text.strip()
            lvl2_link = lvl2.get_attribute("href")
            category_links.append((lvl2_name, lvl2_link))
            log_message(f"Finding level-2: {lvl2_name, lvl2_link}", text_box)
            lvl2_id = insert_category_to_db(lvl2_name, lvl2_link, parent_id)
            # Hover lên level-2 để menu cấp 3 hiện ra
            actions.move_to_element(lvl2).perform()
            log_message(f"Hovered to level-2: {lvl2_name}", text_box)
            # **Chỉ sau khi hover mới tìm cấp 3**
            level_three_buttons = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//nav[contains(@class,'popper')]//div[contains(@id,'level-three')]//li/a")
                )
            )
            for lvl3 in level_three_buttons:
                lvl3_name = lvl3.text.strip()
                lvl3_link = lvl3.get_attribute("href")
                category_links.append((lvl3_name, lvl3_link))
                lvl3_id = insert_category_to_db(lvl3_name, lvl3_link, lvl2_id)
                log_message(f"Finding level-3: {lvl3_name}", text_box)
    log_message("Extract all category links successfully")
    driver.quit()

def get_course_link_from_topic(text_box, headless=False):

def get_site_links_from_main_page(text_box, headless=False):
    website = "https://www.udemy.com"
    course_carousel = []

    driver = Driver(
        uc=True,
        browser="chrome",
        locale_code="vi",
        headless=headless,
        window_size="1920, 1080",
    )
    driver.uc_open_with_reconnect(website, 4)

    root_node = None
    next_button = None

    try:
        log_message("Start first scenario", text_box)
        next_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '(//div[@class="component-margin"])[1]//button[@data-pager-type="next"]',
                )
            )
        )
        root_node = '(//div[@class="component-margin"])[1]'
    except selenium.common.exceptions.TimeoutException:
        try:
            log_message("Udemy UI changed, switching to second scenario", text_box)
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//section[@id="discovery-units-top"]//button[@data-pager-type="next"]',
                    )
                )
            )
            root_node = '//section[@id="discovery-units-top"]'
        except selenium.common.exceptions.TimeoutException:
            try:
                log_message("Udemy UI changed, switching to third scenario", text_box)
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//section[@id="discovery-units-lower"]//button[@data-pager-type="next"]',
                        )
                    )
                )
                root_node = '//div[@data-testid="course-unit-carousel"]'
            except selenium.common.exceptions.TimeoutException:
                log_message(
                    "All three scenarios failed, recommend switching to non-headless mode to run.",
                    text_box,
                )
                if headless:
                    root = tk.Tk()
                    root.withdraw()
                    result = messagebox.askyesno(
                        "Switch to Non-Headless Mode",
                        "All three scenarios failed. Do you want to rerun in non-headless mode?",
                    )
                    root.destroy()
                    if result:
                        driver.quit()
                        return get_site_links_from_main_page(text_box, headless=False)
                    else:
                        pass
                else:
                    pass

    headless_mode_failed = False

    if next_button is None or root_node is None:
        log_message("Let's not try to get all suggest courses", text_box)
        headless_mode_failed = True
        course_carousel = driver.find_elements(
            By.XPATH, f'//section[@id="discovery-units-top"]//div[@data-index]'
        )
        log_message("Taking suggest course sucessfully", text_box)

    if not headless_mode_failed:
        course_carousel_xpath = f"{root_node}//div[@data-index]"
        log_message("Taking Udemy's suggested courses area", text_box)
        while next_button.is_displayed():
            tmp_course_carousel = driver.find_elements(By.XPATH, course_carousel_xpath)
            log_message("Clicking next button", text_box)
            next_button.click()
            if len(tmp_course_carousel) > 15:
                break
            time.sleep(3)
        course_carousel = driver.find_elements(By.XPATH, course_carousel_xpath)

    log_message("Extracting links from elements", text_box)
    links = []
    count = 0
    for item in course_carousel:
        try:
            count += 1
            if count > 4:
                break
            href = item.find_element(By.XPATH, ".//a").get_attribute("href")
            links.append(href)
        except selenium.common.exceptions.NoSuchElementException:
            continue

    log_message(f"Found {count} links", text_box)
    driver.quit()

    return links

def get_comments_in_course(links, text_box, headless=False):
    driver = Driver(uc=True, browser="chrome", locale_code="vi", headless1=headless)
    courses_info = []

    try:
        for link in links:
            if is_course_in_db(link):
                log_message(f"Course link already exists in database: {link}", text_box)
                continue

            index = 0
            log_message(f"Processing link: {link}", text_box)
            driver.maximize_window()
            driver.uc_open_with_reconnect(link, 4)

            try:
                course_name = (
                    WebDriverWait(driver, 15)
                    .until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//h1[@data-purpose="lead-title"]')
                        )
                    )
                    .text
                )
                log_message(
                    f"Course name retrieved successfully: {course_name}", text_box
                )
            except selenium.common.exceptions.TimeoutException as e:
                log_message(f"Error retrieving course name: {e}", text_box)
                course_name = "not_found"

            try:
                course_category = (
                    WebDriverWait(driver, 15)
                    .until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//div[contains(@class, "topic-menu")]/div/a')
                        )
                    )
                    .text
                )
                log_message(
                    f"Course category retrieved successfully: {course_category}",
                    text_box,
                )
            except selenium.common.exceptions.TimeoutException as e:
                log_message(f"Error retrieving course category: {e}", text_box)
                course_category = "not_found"

            try:
                review_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//div[@data-purpose="reviews"]/button')
                    )
                )
                review_button.click()
            except Exception as e:
                log_message(f"Error clicking review button: {e}", text_box)
                continue

            data_feedback_list = []

            while True:
                try:
                    show_more_button = driver.find_element(
                        By.XPATH, '//button[@data-purpose="show-more-review-button"]'
                    )
                    tmp_count = driver.find_elements(
                        By.XPATH, '//ul[contains(@class, "reviews-modal")]/li'
                    )
                    if len(tmp_count) > 30:
                        break
                    show_more_button.click()
                    log_message("Loading more reviews", text_box)
                    time.sleep(3)
                except NoSuchElementException:
                    break
                except Exception as e:
                    log_message(
                        f"Error clicking 'Show More Reviews' button: {e}", text_box
                    )
                    break

            try:
                review_items = driver.find_elements(
                    By.XPATH, '//ul[contains(@class, "reviews-modal")]/li'
                )
                log_message(f"Found {len(review_items)} reviews", text_box)
            except NoSuchElementException:
                log_message("No reviews found", text_box)
                continue

            log_message("Extracting review content", text_box)
            for item in review_items:
                try:
                    feedback_elements = item.find_elements(
                        By.XPATH,
                        './/div[contains(@class, "show-more-module")]//div[@tabindex=-1]/p',
                    )
                    feedback_text = " ".join(
                        [
                            elem.text.replace("\n", " ").replace(",", " ")
                            for elem in feedback_elements
                        ]
                    )
                    data_feedback_list.append(feedback_text)
                except Exception as e:
                    log_message(f"Error extracting review: {e}", text_box)
                    continue

            course_name_sanitized = re.sub(r'[\\/*?:"<>|]', "_", course_name)
            comments_filename = f"reviews-{course_name_sanitized}.csv"
            with open(comments_filename, "w", encoding="utf-8", newline="") as csvfile:
                csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                csvwriter.writerow(["Comment"])
                for comment in data_feedback_list:
                    csvwriter.writerow([comment])

            insert_course_to_db(course_name, course_category, link)
            log_message("Stored course information successfully")
            insert_comment_to_db(data_feedback_list, course_name)
            log_message("Stored course's comments successfully")
            log_message(f"Reviews saved for course: {course_name}", text_box)

            courses_info.append(
                {
                    "CourseName": course_name,
                    "CourseCategory": course_category,
                    "CourseLink": link,
                }
            )

        with open("courses_info.csv", "w", encoding="utf-8", newline="") as csvfile:
            fieldnames = ["CourseName", "CourseCategory", "CourseLink"]
            csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            csvwriter.writeheader()
            for course in courses_info:
                csvwriter.writerow(course)

    finally:
        driver.quit()
        log_message("Driver closed.", text_box)

def run_automatically(text_box, headless):
    links = get_site_links_from_main_page(text_box, headless)
    get_comments_in_course(links, text_box, headless)
    log_message("Automatic process completed.", text_box)

def run_manually(text_box, link_entry, headless):
    log_message("Start run at manual mode", text_box)
    link = link_entry.get()
    if not link:
        messagebox.showerror("Error", "Please enter link.")
        return
    links = [link]
    get_comments_in_course(links, text_box, headless)
    log_message("Manual process completed.", text_box)
    
def run_category(text_box, headless):
    log_message("Start extracting category", text_box=text_box)
    get_category_links_from_main_page(text_box=text_box)

def create_gui():
    root = tk.Tk()
    root.title("Udemy Course Scraper")
    root.geometry("600x400")
    root.configure(bg="#33302E")
    link_label = tk.Label(root, text="Enter link:", bg="#33302E", fg="white")
    link_label.pack(pady=5)
    link_entry = tk.Entry(root, width=70, bg="#383533", fg="white")
    link_entry.pack(pady=5)
    headless_var = IntVar()
    headless_checkbox = tk.Checkbutton(
        root,
        text="Headless Mode",
        variable=headless_var,
        bg="#33302E",
        fg="white",
        selectcolor="#33302E",
    )
    headless_checkbox.pack(pady=5)
    auto_button = tk.Button(
        root,
        text="Run automatically (demo sequence)",
        command=lambda: Thread(
            target=run_automatically, args=(text_box, headless_var.get())
        ).start(),
        bg="#383533",
        fg="white",
    )
    auto_button.pack(pady=5)
    manual_button = tk.Button(
        root,
        text="Run manually",
        command=lambda: Thread(
            target=run_manually, args=(text_box, link_entry, headless_var.get())
        ).start(),
        bg="#383533",
        fg="white",
    )
    run_category_button = tk.Button(
        root,
        text="Run extract category",
        command=lambda: Thread(
            target=run_category, args=(text_box, headless_var.get())
        ).start(),
        bg="#383533",
        fg="white",
    )
    manual_button.pack(pady=5)
    run_category_button.pack(pady=5)
    text_box = tk.Text(root, height=17, width=70, bg="#383533", fg="white")
    text_box.pack(pady=5)
    root.mainloop()

def main():
    create_database()
    create_gui()

if __name__ == "__main__":
    main()