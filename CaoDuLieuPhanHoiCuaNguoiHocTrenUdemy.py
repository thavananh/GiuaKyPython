import sqlite3
import csv
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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


def get_site_links_from_main_page(text_box, headless=False):
    website = "https://www.udemy.com"
    course_carousel = []

    # Initialize the driver
    driver = Driver(
        uc=True,
        browser="chrome",
        locale_code="vi",
        headless=headless,
        window_size="1920, 1080",
    )
    # driver.maximize_window()

    driver.uc_open_with_reconnect(website, 4)

    # Find the root node for the course carousel
    root_node = None
    next_button = None

    # page_html = driver.get_page_source()
    # with open('udemy_main_page.html', 'w', encoding='utf-8') as f:
    #     f.write(page_html)

    try:
        log_message("Start first scenario", text_box)
        # driver.save_screenshot("scenario1.png")
        next_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '(//div[@class="component-margin"])[1]//button[@data-pager-type="next"]',
                )
            )
        )
        # next_button = driver.find_element(By.XPATH, '(//div[@class="component-margin"])[1]//button[@data-pager-type="next"]')
        root_node = '(//div[@class="component-margin"])[1]'
    except selenium.common.exceptions.TimeoutException:
        try:
            log_message("Udemy UI changed, switching to second scenario", text_box)
            # driver.save_screenshot("scenario2.png")
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//section[@id="discovery-units-top"]//button[@data-pager-type="next"]',
                    )
                )
            )
            # next_button = driver.find_element(By.XPATH, '//section[@id="discovery-units-top"]//button[@data-pager-type="next"]')
            root_node = '//section[@id="discovery-units-top"]'
        except selenium.common.exceptions.TimeoutException:
            try:
                log_message("Udemy UI changed, switching to third scenario", text_box)
                # driver.save_screenshot("scenario3.png")
                # next_button = driver.find_element(By.XPATH, '//section[@id="discovery-units-lower"]//button[@data-pager-type="next"]')
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
                    # Prompt the user to switch to non-headless mode
                    root = tk.Tk()
                    root.withdraw()  # Hide the root window
                    result = messagebox.askyesno(
                        "Switch to Non-Headless Mode",
                        "All three scenarios failed. Do you want to rerun in non-headless mode?",
                    )
                    root.destroy()  # Destroy the root window
                    if result:
                        # User chose Yes, rerun the function in non-headless mode
                        driver.quit()
                        return get_site_links_from_main_page(text_box, headless=False)
                    else:
                        # User chose No, proceed to code below
                        pass
                else:
                    # Already in non-headless mode, proceed
                    pass

    headless_mode_failed = False

    if next_button is None or root_node is None:
        log_message("Let's not try to get all suggest courses", text_box)
        headless_mode_failed = True
        # root_node = ['(//div[@class="component-margin"])[1]', '//section[@id="discovery-units-top"]', '//div[@data-testid="course-unit-carousel"]']
        #'//section[@id="discovery-units-top"]'
        course_carousel = driver.find_elements(
            By.XPATH, f'//section[@id="discovery-units-top"]//div[@data-index]'
        )
        log_message("Taking suggest course sucessfully", text_box)
        # Could not find the next_button, return empty list

    if not headless_mode_failed:
        course_carousel_xpath = f"{root_node}//div[@data-index]"
        # Click the next button until it is no longer displayed
        log_message("Taking Udemy's suggested courses area", text_box)
        while next_button.is_displayed():
            tmp_course_carousel = driver.find_elements(By.XPATH, course_carousel_xpath)
            log_message("Clicking next button", text_box)
            next_button.click()
            if len(tmp_course_carousel) > 15:
                break
            time.sleep(3)
        # Find all course elements in the carousel
        course_carousel = driver.find_elements(By.XPATH, course_carousel_xpath)

    # Extract the links from the course elements
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
            # log_message('No link found', text_box)
            continue

    log_message(f"Found {count} links", text_box)
    # Close the driver
    driver.quit()

    return links


def get_comments_in_course(links, text_box, headless=False):
    driver = Driver(uc=True, browser="chrome", locale_code="vi", headless1=headless)
    courses_info = []

    try:
        # Read the list of links
        for link in links:
            if is_course_in_db(link):
                log_message(f"Course link already exists in database: {link}", text_box)
                continue  # Skip this link

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

            # Wait for the review button to appear and click it
            try:
                review_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//div[@data-purpose="reviews"]/button')
                    )
                )
                review_button.click()
            except Exception as e:
                log_message(f"Error clicking review button: {e}", text_box)
                continue  # Move to the next link if there's an error

            data_feedback_list = []

            # Click "Show More Reviews" button if available
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
                    time.sleep(3)  # Wait for content to load
                except NoSuchElementException:
                    break  # No more "Show More Reviews" button
                except Exception as e:
                    log_message(
                        f"Error clicking 'Show More Reviews' button: {e}", text_box
                    )
                    break

            # Get the list of reviews
            try:
                review_items = driver.find_elements(
                    By.XPATH, '//ul[contains(@class, "reviews-modal")]/li'
                )
                log_message(f"Found {len(review_items)} reviews", text_box)
            except NoSuchElementException:
                log_message("No reviews found", text_box)
                continue

            # Extract review content
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

            # Save comments to CSV file per course
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

            # Append course information to the list
            courses_info.append(
                {
                    "CourseName": course_name,
                    "CourseCategory": course_category,
                    "CourseLink": link,
                }
            )

        # After processing all links, output course information to CSV
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


def create_gui():
    root = tk.Tk()
    root.title("Udemy Course Scraper")
    root.geometry("600x400")  # Set window size
    root.configure(bg="#33302E")  # Set background color

    # Create widgets
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
    manual_button.pack(pady=5)

    text_box = tk.Text(root, height=17, width=70, bg="#383533", fg="white")
    text_box.pack(pady=5)

    # Run the GUI
    root.mainloop()


def main():
    create_database()
    create_gui()


if __name__ == "__main__":
    main()
