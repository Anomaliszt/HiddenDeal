async function getAuctions() {
    try {
        const response = await fetch(`${API_URL}/auctions/`);
        const auctions = await response.json();
        displayAuctions(auctions);
    } catch (error) {
        console.error('Error fetching auctions:', error);
    }
}

// DISPLAY AUCTIONS
function displayAuctions(auctions) {
    const auctionsContainer = document.getElementById('auctions-list');
    auctionsContainer.innerHTML = auctions.map(auction => {
        const isExpired = new Date(auction.expires_at) < new Date();
        const status = isExpired ? 'expired' : auction.status;
        
        const itemValue = auction.item_value ? `$${auction.item_value.toFixed(2)}` : 'N/A';
        
        const creatorDisplay = auction.creator_username || `User #${auction.creator_id}`;
        
        return `
            <div class="auction-card">
                <h2>${auction.title}</h2>
                <p>${auction.description}</p>
                <div class="meta">
                    <span class="price">Item Value: ${itemValue}</span>
                    <span class="status-${status.toLowerCase()}">${status.toUpperCase()}</span>
                </div>
                <div class="creator">Created by: ${creatorDisplay}</div>
                <a href="Auction.html?id=${auction.id}" class="view-button">View Auction</a>
            </div>
        `;
    }).join('');
}

function startAuctionRefresh() {
    getAuctions();
    
    setInterval(getAuctions, 30000);
}

document.addEventListener('DOMContentLoaded', startAuctionRefresh);