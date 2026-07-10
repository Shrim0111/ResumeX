
function _defineProperty(obj, key, value) {if (key in obj)
   {Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true });}
    else {obj[key] = value;}return obj;}const ANIMATION_DURATION = 300;

const SIDEBAR_EL = document.getElementById("sidebar");

const SUB_MENU_ELS = document.querySelectorAll(
".menu > ul > .menu-item.sub-menu");


const FIRST_SUB_MENUS_BTN = document.querySelectorAll(
".menu > ul > .menu-item.sub-menu > a");


const INNER_SUB_MENUS_BTN = document.querySelectorAll(
".menu > ul > .menu-item.sub-menu .menu-item.sub-menu > a");



//NORMAL JS

document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll(".tab-button");
  const forms = document.querySelectorAll(".form-section");
  
  buttons.forEach(button => {
      button.addEventListener("click", function () {
          const target = this.getAttribute("data-target");
          
          forms.forEach(form => {
              form.classList.remove("active");
          });
          
          document.getElementById(target).classList.add("active");
      });
  });
});


// login and register button functionality


