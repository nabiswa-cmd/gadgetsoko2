// Get cart from localStorage (guest cart)
let cart = JSON.parse(localStorage.getItem('guestCart')) || [];

const cartItemsContainer = document.getElementById('cartItems');
const cartTotalEl = document.getElementById('cartTotal');

document.addEventListener("DOMContentLoaded", () => {
    renderCart();
});

function renderCart() {
    cartItemsContainer.innerHTML = '';
    let total = 0;

    if(cart.length === 0){
        cartItemsContainer.innerHTML = '<p>Your cart is empty.</p>';
        cartTotalEl.innerText = '0.00';
        return;
    }

    cart.forEach((item, index) => {
        total += parseFloat(item.price);

        const div = document.createElement('div');
        div.className = 'cart-item';
        div.innerHTML = `
            <img src="${item.image}" alt="${item.name}">
            <div class="cart-item-info">
                <h4>${item.name}</h4>
                <p>KSh ${item.price}</p>
            </div>
            <button onclick="removeItem(${index})">Remove</button>
        `;
        cartItemsContainer.appendChild(div);
    });

    cartTotalEl.innerText = total.toFixed(2);
}

function removeItem(index) {
    cart.splice(index, 1);
    localStorage.setItem('guestCart', JSON.stringify(cart));
    renderCart();
}