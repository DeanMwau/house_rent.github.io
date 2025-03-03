// Scroll images
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


// Get the input element where the user types the location
const locationInput = document.getElementById('location-input');
const apartmentListContainer = document.getElementById('apartment-list');

// Add event listener for input event (triggered as user types)
locationInput.addEventListener('input', function () {
    const location = locationInput.value.trim();  // Get the input value

    if (location.length > 0) {
        // Call the API to get apartments by location as the user types
        fetch(`/api/apartments?location=${location}`)
            .then(response => response.json())
            .then(data => {
                apartmentListContainer.innerHTML = ''; // Clear previous results

                if (data.apartments && data.apartments.length > 0) {
                    // Loop through apartments and display each
                    data.apartments.forEach(apartment => {
                        const apartmentItem = document.createElement('div');
                        apartmentItem.classList.add('apartment-item', 'mb-4');

                        apartmentItem.innerHTML = `
                            <h4 style="color:rgb(0, 64, 255);">${apartment.title}</h4>
                            <p style="color:rgb(8, 15, 36);">${apartment.description}</p>
                            <p style="color:rgb(8, 15, 36);"><strong>Location:</strong> ${apartment.location}</p>
                            <p style="color:rgb(8, 15, 36);"><strong>Rent:</strong> Ksh ${apartment.rent}</p>
                        `;
                        apartmentListContainer.appendChild(apartmentItem);
                    });
                } else {
                    // Display message if no apartments are found
                    apartmentListContainer.innerHTML = '<p style="color:rgb(8, 15, 36);">No apartments found for this location.</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching apartments:', error);
                apartmentListContainer.innerHTML = '<p style="color:rgb(8, 15, 36);">Error loading apartments.</p>';
            });
    } else {
        // If input is empty, clear the results
        apartmentListContainer.innerHTML = '';
    }
});
