


    document.addEventListener("DOMContentLoaded", function () {
                    const containers = document.querySelectorAll(".apartment-images-container");

                    containers.forEach((container) => {
                        const images = container.querySelector(".apartment-images");

                        container.addEventListener("click", (event) => {
                            const containerWidth = container.offsetWidth;
    const clickX = event.clientX - container.getBoundingClientRect().left;

                            // Check if the click is on the right half of the container
                            if (clickX > containerWidth / 2) {
        // Scroll to the next image
        images.scrollBy({ left: containerWidth, behavior: "smooth" });
                            } else {
        // Scroll to the previous image
        images.scrollBy({ left: -containerWidth, behavior: "smooth" });
                            }
                        });
                    });
                });