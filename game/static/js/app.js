'use strict'

const wsClient = new WebSocket("ws://localhost:5000/listen")

class Users extends React.Component {
    handleNewGame = (userId, event) => {
        fetch('/api/games', {
            credentials: 'include',
            method: 'POST',
            body: JSON.stringify({'player': userId}),
            headers: {'Content-Type': 'application/json'}
        }) .then( response => {
            if (!response.ok) {
                response.text().then(res => alert(res))
            }
        })
    }

    render() {
        return (
            <div className="col-3">
                <h2>Users</h2>
                <small>Click an opponent to start a new game!</small>
                <ul>
                { this.props.users.map((user, i) => (
                    <li><a onClick={this.handleNewGame.bind(this, user.id)} key={i}>{user.id}, {user.name}</a></li>
                    )) 
                }
                </ul>
            </div>
        )
    }

}

class Games extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            gameId: null
        }
    }

    showGame = (game, gameId, event) => {
        this.setState({
            gameId: gameId
        })
        this.forceUpdate()

    }
    
    render() {
        const getUser = (userId) => {
            return this.props.users.filter((user) => user.id == userId)[0]
        }

        const gameStr = (game) => getUser(game.player1).name + ' v. ' + getUser(game.player2).name

        return (
            <div className="col-9">
                <div className="row">
                    <div className="col-4">
                        <h2>Games</h2>
                        <small>Select a game to view.</small>
                        <ul>
                        { this.props.games.map((game, i) => (
                            <li><a key={i} onClick={this.showGame.bind(this, game, i)}>{gameStr(game)}</a></li>
                          )) 
                        }
                        </ul>
                    </div>
                    <div className="col-8">
                        <Game games={this.props.games} gameId={this.state.gameId} />
                    </div>
                </div>
            </div>
        )
    }
}

class Game extends React.Component {
    handleMove = (loc, event) => {
        fetch('/api/games/' + this.props.gameId, {
            credentials: 'include',
            method: 'POST',
            body: JSON.stringify({'location': loc}),
            headers: {'Content-Type': 'application/json'}
        }) .then( response => {
            if (!response.ok) {
                response.text().then(res => alert(res))
            }
        })
    }

    render() {
        if (this.props.gameId == null) {
            return <h2>Game</h2>
        }
        const game = this.props.games[this.props.gameId]
        return (
            <div>
                <h2>Game</h2>
                <div>turn: {game.turn}</div>
                <div>result: {game.result}</div>
                <div>
                    <ul className="board">
                    { game.board.map((move, i) => (
                        <li className="square col-4" key={i} onClick={this.handleMove.bind(this, i)}>{move}</li>
                      ))
                    }
                    </ul>
                </div>
            </div>
        )
    }

}

class App extends React.Component {

    constructor(props) {
        super(props)
        this.state = {
            userId: null,
            users: [],
            games: [],
        }
    }

    componentDidMount() {
        wsClient.onmessage = (message) => {
            var data = JSON.parse(message.data)
            Object.keys(data).map((key, i) => {
                this.setState({
                    [key]: data[key]
                })
            })
        }
    }

    handleUserUpdate = (event) => {
        fetch('/api/username', {
            credentials: 'include',
            method: 'POST',
            body: JSON.stringify({'username': event.target.value}),
            headers: {'Content-Type': 'application/json'}
        }).then(
            response => {
                if (!response.ok) { console.log(response) }
            }
        )
    }

    render() {
        const user = this.state.users.filter(u => u.id == this.state.userId)[0]
        if (!user) {
            return <div>need user</div>
        }

        return (
            <div className="container">
                <div className="row my-3">
                    <div className="col-3">
                        <div className="form-group">
                            <label>user id: </label>
                            {user.id}
                        </div>
                        <div className="form-group">
                            <label for="username">username</label>
                            <input type="text" name="username" value={user.name} onChange={this.handleUserUpdate} />
                            <div><small>Enter a username to update.</small></div>
                        </div>
                    </div>
                </div>
                <div className="row">
                    <Users users={this.state.users} />
                    <Games games={this.state.games} users={this.state.users}/>
                </div>
            </div>
        )
    }
}

ReactDOM.render(
    React.createElement(App),
    document.getElementById('root')
)
