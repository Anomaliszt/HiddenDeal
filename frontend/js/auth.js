async function login(email, password) {
    try {
        const loginUrl = `${API_URL}/auth/login`;
        console.log('Attempting login at:', loginUrl);

        const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        
        if (response.ok && data.token) {
            localStorage.setItem('token', data.token);
            window.location.href = 'index.html';
            return { success: true };
        } else {
            return { 
                success: false, 
                message: data.message || 'Invalid credentials'
            };
        }
    } catch (error) {
        console.error('Login error:', error);
        return { 
            success: false, 
            message: 'Login failed. Please try again.'
        };
    }
}

async function register(username, email, password) {
    try {
        console.log('Making registration request to:', `${API_URL}/auth/register`);
        
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                email: email,
                password: password
            })
        });
        
        console.log('Registration response status:', response.status);
        const data = await response.json();
        console.log('Registration response data:', data);
        
        if (response.ok) {
            alert('Registration successful! Please login.');
            return true;
        } else {
            throw new Error(data.message || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('Registration failed: ' + error.message);
        return false;
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'index.html';
}

function updateAuthUI() {
    const authButtons = document.getElementById('auth-buttons');
    if (!authButtons) {
        console.warn('Auth buttons container not found in the current page');
        return;
    }

    const token = localStorage.getItem('token');
    if (token) {
        authButtons.innerHTML = '<button onclick="logout()">Logout</button>';
    } else {
        authButtons.innerHTML = `
            <a href="login.html"><button>Login</button></a>
            <a href="register.html"><button>Register</button></a>
        `;
    }
}