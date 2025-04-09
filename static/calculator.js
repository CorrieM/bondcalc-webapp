function calculateInvestment(data) {
    // Property Parameters (Default values from Excel)
    const propertyParams = {
        levies: 1200,
        rentalIncome: 8500,
        capitalGrowth: 0.06, // 6%
        ratesAndTaxes: 800,
        rentalManagement: 0.085, // 8.5%
        rentalEscalation: 0.06, // 6%
        rentalInsurance: 250,
        bondRepayment: 7850,
        interestRate: 0.115, // 11.5%
        propertyValue: 1000000, // Initial property value
        drawdownRate: 0.05, // 5%
        annualDrawdownIncrease: 0.06 // 6%
    };

    // Input parameters
    const monthlyPremium = data.monthlyPremium;
    const annualIncrease = data.annualIncrease / 100;
    const investmentReturn = data.investmentReturn / 100;
    const term = data.term;
    const lumpsum = data.lumpsum;
    const actualProperties = data.actual;

    // IGrow Calculations
    const yearlyRentalIncome = propertyParams.rentalIncome * 12;
    const yearlyExpenses = (propertyParams.levies + propertyParams.ratesAndTaxes + propertyParams.rentalInsurance) * 12;
    const yearlyBondRepayment = propertyParams.bondRepayment * 12;
    const rentalManagementFee = yearlyRentalIncome * propertyParams.rentalManagement;
    const totalYearlyExpenses = yearlyExpenses + rentalManagementFee;
    
    // First Year Calculations for IGrow
    const igrowOneYearContribution = -(monthlyPremium * 12);
    const propertyValue = propertyParams.propertyValue;
    const igrowEquity = propertyValue * propertyParams.capitalGrowth * actualProperties;
    const rentalIncome = yearlyRentalIncome * actualProperties;
    const expenses = totalYearlyExpenses * actualProperties;
    const bondRepayments = yearlyBondRepayment * actualProperties;
    
    const igrowOneYearCashflow = rentalIncome - expenses - bondRepayments;
    const igrowOneYearFinancialPosition = igrowEquity + igrowOneYearCashflow;
    const igrowTotalContribution = igrowOneYearContribution;

    // Calculate property portfolio value after term years
    let portfolioValue = propertyValue * actualProperties;
    let currentRentalIncome = rentalIncome;
    let currentExpenses = expenses;
    
    for (let i = 0; i < term; i++) {
        portfolioValue *= (1 + propertyParams.capitalGrowth);
        currentRentalIncome *= (1 + propertyParams.rentalEscalation);
        currentExpenses *= (1 + propertyParams.rentalEscalation);
    }

    // Traditional Investment Calculations
    let traditionalValue = lumpsum;
    let traditionalMonthlyContribution = monthlyPremium;
    for (let i = 0; i < term; i++) {
        traditionalValue = (traditionalValue + (traditionalMonthlyContribution * 12)) * (1 + investmentReturn);
        traditionalMonthlyContribution *= (1 + annualIncrease);
    }

    // Calculate monthly incomes at retirement
    const igrowMonthlyIncome = (currentRentalIncome - currentExpenses) / 12;
    const traditionalMonthlyIncome = (traditionalValue * propertyParams.drawdownRate) / 12;

    // Present Value calculations
    const discountRate = 0.08; // 8% discount rate
    const igrowPVMonthlyIncome = igrowMonthlyIncome / Math.pow(1 + discountRate, term);
    const traditionalPVMonthlyIncome = traditionalMonthlyIncome / Math.pow(1 + discountRate, term);

    // Internal Rate of Return (simplified)
    const igrowIRR = ((igrowOneYearFinancialPosition / Math.abs(igrowOneYearContribution)) - 1) * 100;
    const traditionalIRR = (investmentReturn * 100);

    return {
        financial_position: {
            igrow: {
                "Equity & Cash Reserves": portfolioValue,
                "Monthly Income": igrowMonthlyIncome,
                "PV Monthly Income": igrowPVMonthlyIncome
            },
            traditional: {
                "Financial Position": traditionalValue,
                "Monthly Income": traditionalMonthlyIncome,
                "PV Monthly Income": traditionalPVMonthlyIncome
            }
        },
        investment_comparison: {
            igrow: {
                "Property": "Middle Class - 2 Bed 1 Bath",
                "1 Year Contribution": igrowOneYearContribution,
                "1 Year Total Cashflow": igrowOneYearCashflow,
                "Equity through Capital Appreciation": igrowEquity,
                "1 Year Financial Position": igrowOneYearFinancialPosition,
                "1 Year Total Contribution": igrowTotalContribution,
                "Internal Rate of Return": igrowIRR,
                "Total Return": (igrowOneYearFinancialPosition / Math.abs(igrowOneYearContribution)) * 100
            },
            traditional: {
                "Investment Type": "Money Market",
                "1 Year Premium Monthly": monthlyPremium,
                "1 Year Value Instrument": traditionalValue,
                "1 Year Lumpsum": lumpsum,
                "1 Year Financial Position": traditionalValue,
                "1 Year Total Contribution": monthlyPremium * 12,
                "Internal Rate of Return": traditionalIRR,
                "Total Return": (traditionalValue / (lumpsum + monthlyPremium * 12)) * 100
            }
        },
        leveraged_strategy: {
            igrow: {
                "Properties": actualProperties,
                "Property Portfolio Value": portfolioValue,
                "Retirement Income": igrowMonthlyIncome * 12,
                "PV of Retirement Income": igrowPVMonthlyIncome * 12
            },
            traditional: {
                "Financial Position": traditionalValue,
                "PV of Retirement Income": traditionalPVMonthlyIncome * 12
            }
        }
    };
}

function displayResults(results) {
    const resultsList = document.getElementById('resultsList');
    resultsList.innerHTML = '';
    
    // Function to format currency
    const formatCurrency = (value) => {
        return new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            currency: 'ZAR',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    };

    // Display IGrow Results
    resultsList.innerHTML += '<h4 style="margin-top: 20px; color: var(--primary-color);">IGrow Investment</h4>';
    Object.entries(results.financial_position.igrow).forEach(([key, value]) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${key}:</span><span>${formatCurrency(value)}</span>`;
        resultsList.appendChild(li);
    });

    // Display Traditional Results
    resultsList.innerHTML += '<h4 style="margin-top: 20px; color: var(--primary-color);">Traditional Investment</h4>';
    Object.entries(results.financial_position.traditional).forEach(([key, value]) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${key}:</span><span>${formatCurrency(value)}</span>`;
        resultsList.appendChild(li);
    });

    // Display Investment Comparison
    resultsList.innerHTML += '<h4 style="margin-top: 20px; color: var(--primary-color);">Investment Comparison</h4>';
    Object.entries(results.investment_comparison.igrow).forEach(([key, value]) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>IGrow ${key}:</span><span>${formatCurrency(value)}</span>`;
        resultsList.appendChild(li);
    });
    Object.entries(results.investment_comparison.traditional).forEach(([key, value]) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>Traditional ${key}:</span><span>${formatCurrency(value)}</span>`;
        resultsList.appendChild(li);
    });

    document.getElementById('results').style.display = 'block';
} 