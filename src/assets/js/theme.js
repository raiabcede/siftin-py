//add Shadow to header on scroll
document.addEventListener("DOMContentLoaded", function () {
    const topHeader = document.querySelector(".top-header");
    if (!topHeader) return;
    
    document.addEventListener("scroll", function () {
        if (document.body.scrollTop > 60 || document.documentElement.scrollTop > 60) {
            topHeader.classList.add("shadow-sm");  
        } else {
            topHeader.classList.remove("shadow-sm");
        }
    });
});

//Toaster Js
document.addEventListener("DOMContentLoaded", function () {
  const dismissToast = document.getElementById('dismiss-toast');
  
  if (dismissToast) {
    // Show toast after 1 second
    setTimeout(() => {
      dismissToast.classList.add('show-toast'); 
    }, 1000);

    // Hide and remove toast after 5 seconds
    setTimeout(() => {
      dismissToast.classList.add('hs-removing'); 
      dismissToast.classList.remove('show-toast'); 
      setTimeout(() => {
        dismissToast.remove();
      }, 300);  
    }, 5000);
  }
});