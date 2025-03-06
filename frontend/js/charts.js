let bidChart = null;
let allAuctionBids = [];

// AUCTION DETAILS 
async function loadAuctionDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    const auctionId = urlParams.get('id');
    const token = localStorage.getItem('token');
    
    if (!token) {
        alert('Please login to view auction details');
        window.location.href = 'login.html';
        return;
    }
    
    try {
        // FETCH AUCTION DETAILS
        const auctionResponse = await fetch(`${API_URL}/auctions/${auctionId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const auction = await auctionResponse.json();
        
        // FETCH AUCTION BIDS
        const allBidsResponse = await fetch(`${API_URL}/auctions/${auctionId}/bids`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const allBids = await allBidsResponse.json();
        allAuctionBids = allBids;
        
        displayAuctionDetails(auction);
        
        // DISPLAY CURRENT WINNER
        if (auction.lowest_unique_bid) {
            const winnerInfo = document.createElement('p');
            winnerInfo.innerHTML = `Current Winner: <strong>${auction.lowest_unique_bid.username}</strong>`;
            if (auction.lowest_unique_bid.is_users_bid) {
                winnerInfo.innerHTML += ' <span class="winner-badge">★ You</span>';
            }
            document.querySelector('.auction-meta').appendChild(winnerInfo);
        }
        
        displayBidsHistory(auction.bids);
        
        updateBidChart(allBids);
        
        await fetchAndDisplayPoolPrizeInfo(auctionId);
    } catch (error) {
        console.error('Error fetching auction details:', error);
    }
    
    // EXPIRATION CHECK FOR LIVE UPDATES
    setInterval(checkExpiration, 1000);
}

function displayAuctionDetails(auction) {
    document.getElementById('auction-title').textContent = auction.title;
    document.getElementById('auction-description').textContent = auction.description;
    document.getElementById('starting-price').textContent = `$${auction.starting_price}`;
    
    // STATUS CHECK
    const isExpired = new Date(auction.expires_at) < new Date();
    const status = isExpired ? 'expired' : auction.status;
    
    const statusElement = document.getElementById('auction-status');
    statusElement.textContent = status.toUpperCase();
    statusElement.className = '';
    statusElement.classList.add('status', `status-${status.toLowerCase()}`);
    
    const expiresAtElement = document.getElementById('expires-at');
    expiresAtElement.textContent = new Date(auction.expires_at).toLocaleString();
    expiresAtElement.setAttribute('data-expires', auction.expires_at);
    
    // DISABLE BIDS IF AUCTION EXPIRED
    const bidSection = document.querySelector('.bid-card');
    if (isExpired || status === 'expired') {
        bidSection.style.opacity = '0.5';
        document.getElementById('bid-slider').disabled = true;
        document.getElementById('bid-amount').disabled = true;
        document.getElementById('place-bid-btn').disabled = true;
        document.getElementById('place-bid-btn').textContent = 'Auction Expired';
    }
}

function checkExpiration() {
    const expiresAt = document.getElementById('expires-at')?.getAttribute('data-expires');
    if (!expiresAt) return;
    
    const isExpired = new Date(expiresAt) < new Date();
    if (isExpired) {
        const statusElement = document.getElementById('auction-status');
        if (statusElement && !statusElement.classList.contains('status-expired')) {
            statusElement.textContent = 'EXPIRED';
            statusElement.className = 'status status-expired';
            
            const bidSection = document.querySelector('.bid-card');
            if (bidSection) {
                bidSection.style.opacity = '0.5';
                document.getElementById('bid-slider').disabled = true;
                document.getElementById('bid-amount').disabled = true;
                document.getElementById('place-bid-btn').disabled = true;
                document.getElementById('place-bid-btn').textContent = 'Auction Expired';
            }
        }
    }
}

function displayBidsHistory(bids) {
    const bidsList = document.getElementById('bids-list');
    bidsList.innerHTML = '';
    
    if (bids.length === 0) {
        bidsList.innerHTML += '<p>You haven\'t placed any bids on this auction yet.</p>';
        return;
    }
    
    bids.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // BID VISUALIZATION
    bids.forEach(bid => {
        const bidElement = document.createElement('div');
        bidElement.className = 'bid-item';
        
        let statusBadges = '';
        if (bid.is_unique) {
            statusBadges += '<span class="unique-badge">✓ Unique</span>';
        } else {
            statusBadges += '<span class="not-unique-badge">✗ Not Unique</span>';
        }
        
        if (bid.is_winner) {
            statusBadges += '<span class="winner-badge">★ Winning</span>';
        }
        
        bidElement.innerHTML = `
            <div class="bid-item-content">
                <span class="bid-amount">$${bid.amount}</span>
                <span class="bid-time">${new Date(bid.created_at).toLocaleString()}</span>
                <div class="bid-status">
                    ${statusBadges}
                </div>
            </div>
        `;
        bidsList.appendChild(bidElement);
    });
}

function updateBidChart(bids) {
    const ctx = document.getElementById('bidChart').getContext('2d');
    
    const bidRanges = {};
    bids.forEach(bid => {
        const range = Math.floor(bid.amount / 10) * 10;
        bidRanges[range] = (bidRanges[range] || 0) + 1;
    });
    
    if (bidChart) {
        bidChart.destroy();
    }
    
    const sortedRanges = Object.keys(bidRanges).sort((a, b) => Number(a) - Number(b));
    
    bidChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedRanges.map(range => `$${range}-${Number(range)+10}`),
            datasets: [{
                label: 'All Bids Distribution',
                data: sortedRanges.map(range => bidRanges[range]),
                backgroundColor: 'rgba(0, 123, 255, 0.5)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

async function placeBid() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const auctionId = urlParams.get('id');
        const amount = parseFloat(document.getElementById('bid-amount').value);
        
        // VALIDATE
        if (!auctionId) {
            alert('Invalid auction ID');
            return;
        }
        
        if (isNaN(amount) || amount <= 0) {
            alert('Please enter a valid positive bid amount');
            return;
        }

        const token = localStorage.getItem('token');
        if (!token) {
            alert('Please login to place a bid');
            window.location.href = 'login.html';
            return;
        }

        // AUCTION STATUS CHECK
        const expiresAt = document.getElementById('expires-at').getAttribute('data-expires');
        if (new Date(expiresAt) < new Date()) {
            alert('This auction has expired');
            return;
        }

        // VDECIMAL CHECK
        if (amount % 1 !== 0 && amount.toFixed(1) !== amount.toString()) {
            alert('Please enter a whole number or a number with at most one decimal place');
            return;
        }

        const response = await fetch(`${API_URL}/bids/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                auctionId: parseInt(auctionId),
                amount: amount
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Error placing bid');
        }

        await updateWalletDisplay();
        await loadAuctionDetails();
        
        alert('Bid placed successfully!');

    } catch (error) {
        console.error('Error placing bid:', error);
        alert(error.message || 'Error placing bid');
    }
}

// DISPLAY TOP BIDDERS
async function fetchAndDisplayTopBidders(auctionId) {
    try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        if (allAuctionBids.length > 0) {
            calculateAndDisplayTopBidders(allAuctionBids);
            return;
        }
        
        const response = await fetch(`${API_URL}/auctions/${auctionId}/bids`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch bid data');
        const bids = await response.json();
        
        calculateAndDisplayTopBidders(bids);
    } catch (error) {
        console.error('Error fetching top bidders:', error);
        document.getElementById('top-bidders-list').innerHTML = 
            '<p>Failed to load top bidders data</p>';
    }
}

function calculateAndDisplayTopBidders(bids) {
    const bidCounts = {};
    const usernames = {};
    
    bids.forEach(bid => {
        const userId = bid.user_id;
        if (userId) {
            bidCounts[userId] = (bidCounts[userId] || 0) + 1;
            
            if (bid.username) {
                usernames[userId] = bid.username;
            }
        }
    });
    
    const sortedBidders = Object.entries(bidCounts)
        .map(([userId, count]) => ({ 
            userId, 
            count, 
            username: usernames[userId] || `User #${userId}` 
        }))
        .sort((a, b) => b.count - a.count);
    
    const topBiddersList = document.getElementById('top-bidders-list');
    topBiddersList.innerHTML = '';
    
    if (sortedBidders.length === 0) {
        topBiddersList.innerHTML = '<p>No bids yet</p>';
        return;
    }
    
    const topBidders = sortedBidders.slice(0, 10);
    
    topBidders.forEach((bidder, index) => {
        const bidderElement = document.createElement('div');
        bidderElement.className = 'top-bidder-item';
        
        bidderElement.innerHTML = `
            <span class="top-bidder-rank">TOP ${index + 1}:</span>
            <span class="top-bidder-username">${bidder.username}</span>
            <span class="top-bidder-count">participated ${bidder.count} time${bidder.count !== 1 ? 's' : ''}</span>
        `;
        
        topBiddersList.appendChild(bidderElement);
    });
}

// DISPLAY POOL PRIZE INFO
async function fetchAndDisplayPoolPrizeInfo(auctionId) {
    try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const response = await fetch(`${API_URL}/auctions/${auctionId}/pool`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch pool prize data');
        const poolInfo = await response.json();
        
        let poolPrizeSection = document.getElementById('pool-prize-section');
        if (!poolPrizeSection) {
            poolPrizeSection = document.createElement('div');
            poolPrizeSection.id = 'pool-prize-section';
            poolPrizeSection.className = 'pool-prize-section';
            
            document.querySelector('.auction-stats-grid').appendChild(poolPrizeSection);
        }
        
        let poolContent = `
            <h3>Pool Prize Information</h3>
        `;
        
        if (poolInfo.item_value) {
            poolContent += `
                <p>Item Value Threshold: <strong>$${poolInfo.item_value.toFixed(2)}</strong></p>
            `;
        }
        
        poolContent += `
            <p>Current Pool Prize: <strong>$${poolInfo.pool_prize.toFixed(2)}</strong></p>
        `;
        
        if (poolInfo.top_bidders && poolInfo.top_bidders.length > 0) {
            poolContent += `<h4>Potential Prize Winners</h4><ul class="pool-prize-winners">`;
            
            poolInfo.top_bidders.forEach(bidder => {
                poolContent += `
                    <li>
                        <span class="bidder-rank">Top ${bidder.rank}:</span>
                        <span class="bidder-name">${bidder.username}</span>
                        <span class="bidder-participation">(${bidder.bid_count} bids)</span>
                        <span class="bidder-percentage">${bidder.potential_percentage}%</span>
                        <span class="bidder-amount">$${bidder.potential_amount.toFixed(2)}</span>
                    </li>
                `;
            });
            
            poolContent += `</ul>`;
        } else {
            poolContent += `<p>No potential winners yet</p>`;
        }
        
        if (poolInfo.pool_distributed && poolInfo.winners && poolInfo.winners.length > 0) {
            poolContent += `<h4>Pool Prize Winners</h4><ul class="pool-prize-actual-winners">`;
            
            poolInfo.winners.forEach(winner => {
                poolContent += `
                    <li>
                        <span class="winner-rank">Rank ${winner.rank}:</span>
                        <span class="winner-name">${winner.username}</span>
                        <span class="winner-percentage">${winner.percentage}%</span>
                        <span class="winner-amount">$${winner.amount.toFixed(2)}</span>
                    </li>
                `;
            });
            
            poolContent += `</ul>`;
        }
        
        poolPrizeSection.innerHTML = poolContent;
        
    } catch (error) {
        console.error('Error fetching pool prize info:', error);
    }
}