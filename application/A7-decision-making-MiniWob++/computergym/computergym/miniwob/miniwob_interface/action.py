# MiniWoB actions
import abc
import logging

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class MiniWoBAction(object):
    """Defines an action in its __call__ method."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __call__(self, driver):
        """Performs the action defined by this class on the driver.

        Args:
            driver (Selenium WebDriver)
        """
        raise NotImplementedError()

    def to_dict(self):
        """Dict representation for JSON serialization."""
        raise NotImplementedError()


class MiniWoBTerminate(MiniWoBAction):
    """Immediately fails the task.

    This is done via a JavaScript call.
    """

    def __call__(self, driver):
        driver.execute_script('return core.endEpisode(-1,false,"terminate");')

    def __str__(self):
        return "MiniWoBTerminate"

    __repr__ = __str__

    def __eq__(self, other):
        return isinstance(other, MiniWoBTerminate)

    def __hash__(self):
        return hash(self.__class__.__name__)

    def to_dict(self):
        return {"type": "Terminate"}


class MiniWoBPress(MiniWoBAction):
    def __init__(self, left: int, top: int) -> None:
        super().__init__()
        self._move = MiniWoBMove(left, top)

    def __call__(self, driver):
        self._move(driver)

        action = ActionChains(driver)
        action.click_and_hold()
        action.perform()


class MiniWoBRelease(MiniWoBAction):
    def __init__(self, left: int, top: int) -> None:
        super().__init__()
        self._move = MiniWoBMove(left, top)

    def __call__(self, driver):
        self._move(driver)

        action = ActionChains(driver)
        action.release()
        action.perform()


class MiniWoBMove(MiniWoBAction):
    def __init__(self, left: int, top: int) -> None:
        super().__init__()
        self._left = left
        self._top = top

    def __call__(self, driver):
        body = driver.find_element_by_tag_name("body")
        chain = ActionChains(driver)
        chain.move_to_element_with_offset(body, self.left, self.top)
        chain.perform()

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top


class MiniWoBCoordClick(MiniWoBAction):
    """Defines a click action left pixels from the left of the screen and top
    pixels from the top of the screen.

    This is done via Selenium.

    Args:
        left (int): number of pixels from the left of the screen
        top (int): number of pixels from the top of the screen
    """

    def __init__(self, left, top):
        self._left = left
        self._top = top

    def __call__(self, driver):
        """Clicks at coordinates (left, top)"""
        body = driver.find_element_by_tag_name("body")
        chain = ActionChains(driver)
        chain.move_to_element_with_offset(body, self.left, self.top).click().perform()

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top

    def __str__(self):
        return "CoordClick(coords: ({}, {}))".format(self.left, self.top)

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, MiniWoBCoordClick):
            return False
        return (self.left, self.top) == (other.left, other.top)

    def __hash__(self):
        return hash((self.__class__.__name__, self.left, self.top))

    def to_dict(self):
        return {"type": "CoordClick", "left": self._left, "top": self._top}


class MiniWoBElementClickId(MiniWoBAction):
    """An action that clicks on a DOM element regardless of its position
    or visibility.

    This is done via a JavaScript call.

    Args:
        element: One of the following:
            - the DOMElement object to click
            - ref (int) of the DOMElement object to click
        fail_hard (bool): If True, throw an error when the click cannot
            be successfully performed
    """

    def __init__(self, id):
        self.id = id

    def __call__(self, driver):
        element = driver.find_element(By.ID, str(self.id))
        chain = ActionChains(driver)
        chain.move_to_element(element).click().perform()

    def __str__(self):
        return "click(id = {})".format(self.id)

    __repr__ = __str__

    def __eq__(self, other):
        """Compare based on element refs."""
        if not isinstance(other, MiniWoBElementClickId):
            return False
        return (self.ref, self._fail_hard) == (other.ref, other._fail_hard)

    def __hash__(self):
        return hash((self.__class__.__name__, self.ref, self._fail_hard))

    def to_dict(self):
        return {
            "type": "ElementClickId",
            "element": self.id,
        }


class MiniWoBElementClickXpath(MiniWoBAction):
    """An action that clicks on a DOM element regardless of its position
    or visibility.

    This is done via a JavaScript call.

    Args:
        element: One of the following:
            - the DOMElement object to click
            - ref (int) of the DOMElement object to click
        fail_hard (bool): If True, throw an error when the click cannot
            be successfully performed
    """

    def __init__(self, xpath):
        self.xpath = xpath

    def __call__(self, driver: Chrome):
        try:
            elements = driver.find_elements(By.XPATH, str(self.xpath))
        except:
            print(f"Invalid xpath: {self.xpath}")
            return

        if not elements:
            print(f"Invalid xpath: {self.xpath}")
            return

        action_performed = False
        for element in elements:
            try:
                element = WebDriverWait(driver, 0.1).until(
                    EC.element_to_be_clickable(element)
                )

                if element.tag_name == "button":
                    element.click()
                elif element.tag_name == "option":
                    select = Select(element.find_element(By.XPATH, ".."))
                    select.select_by_visible_text(element.text)
                else:
                    chain = ActionChains(driver)

                    chain.move_to_element(element).click().perform()

                action_performed = True

            except Exception as e:
                # print(f"Error message: {e}")

                if "intercept" in str(e):
                    element.send_keys(Keys.ENTER)
                    action_performed = True
                    break
            
            if action_performed:
                break

        if not action_performed:
            print("Click noninteractable element")

    def __str__(self):
        return "click(xpath = {})".format(self.xpath)

    __repr__ = __str__

    def __eq__(self, other):
        """Compare based on element refs."""
        if not isinstance(other, MiniWoBElementClickXpath):
            return False
        return (self.ref, self._fail_hard) == (other.ref, other._fail_hard)

    def __hash__(self):
        return hash((self.__class__.__name__, self.ref, self._fail_hard))

    def to_dict(self):
        return {
            "type": "ElementClickXpath",
            "element": self.xpath,
        }


class MiniWoBType(MiniWoBAction):
    """An action that sends keystrokes to the focused element.

    This is done via Selenium.

    Args:
        text (str or list[str]): Things to type.
            Non-printable characters defined in
            selenium.webdriver.common.keys.Keys can also be used to send
            special keys (arrows, backspace, etc.)
    """

    def __init__(self, text: str):
        self._text = text

    def __call__(self, driver):
        chain = ActionChains(driver)
        chain.send_keys(self._text)
        chain.perform()

    @property
    def text(self):
        return self._text

    def __str__(self):
        return "Type({})".format(repr(self._text))

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, MiniWoBType):
            return False
        return self.text == other.text

    def __hash__(self):
        return hash((self.__class__.__name__, self.text))

    def to_dict(self):
        return {"type": "Type", "text": self.text}


class MiniWoBElementClickOption(MiniWoBAction):
    """An action that clicks on a DOM element regardless of its position
    or visibility.

    This is done via a JavaScript call.

    Args:
        element: One of the following:
            - the DOMElement object to click
            - ref (int) of the DOMElement object to click
        fail_hard (bool): If True, throw an error when the click cannot
            be successfully performed
    """

    def __init__(self, xpath):
        self.xpath = xpath

    def __call__(self, driver: Chrome):
        option_element = driver.find_element(By.XPATH, str(self.xpath))
        select = Select(option_element.find_element(By.XPATH, "./.."))
        select.select_by_visible_text(option_element.text)

    def __str__(self):
        return "clickoption(xpath = {})".format(self.id)

    __repr__ = __str__

    def __eq__(self, other):
        """Compare based on element refs."""
        if not isinstance(other, MiniWoBElementClickOption):
            return False
        return (self.ref, self._fail_hard) == (other.ref, other._fail_hard)

    def __hash__(self):
        return hash((self.__class__.__name__, self.ref, self._fail_hard))

    def to_dict(self):
        return {
            "type": "ElementClickOption",
            "element": self.xpath,
        }


class MiniWoBMoveXpath(MiniWoBAction):
    def __init__(self, xpath):
        self.xpath = xpath

    def __call__(self, driver: Chrome):
        elements = driver.find_elements(By.XPATH, str(self.xpath))

        if not elements:
            print("Invalid xpath")

        action_performed = False
        for element in elements:
            try:
                chain = ActionChains(driver)
                chain.move_to_element(element).perform()

                action_performed = True
            except Exception as e:
                print(e)
                pass

        if not action_performed:
            raise ValueError("Click noninteractable element")
