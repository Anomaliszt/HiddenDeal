// WALLET BALANCE DISPLAY
async function getWalletBalance() {
    const token = localStorage.getItem('token');
    if (!token) return null;

    try {
        const response = await fetch(`${API_URL}/wallet/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();
        return data.balance;
    } catch (error) {
        console.error('Error fetching wallet balance:', error);
        return null;
    }
}

// UPDATE WALLET DISPLAY
async function updateWalletDisplay() {
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('No token found');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/wallet/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch wallet info');
        }

        const data = await response.json();
        const walletBalance = document.getElementById('wallet-balance');
        
        if (walletBalance) {
            walletBalance.textContent = `$${data.balance.toFixed(2)}`;
            
            walletBalance.classList.add('balance-updated');
            setTimeout(() => {
                walletBalance.classList.remove('balance-updated');
            }, 1500);
        }
    } catch (error) {
        console.error('Error updating wallet:', error);
    }
}

